from typing import Optional, List

import scorpyo.util as util
from scorpyo.error import RejectReason, EngineError
from scorpyo.util import LOGGER
from scorpyo.context import Context
from scorpyo.event import (
    BallCompletedEvent,
    BatterInningsCompletedEvent,
    InningsStartedEvent,
    BatterInningsStartedEvent,
    MatchStartedEvent,
    EventType,
    InningsCompletedEvent,
    RegisterTeamLineup,
    record_command,
)
from scorpyo.entity import EntityType
from scorpyo.definitions.innings import InningsState
from scorpyo.innings import Innings
from scorpyo.score import Scoreable
from scorpyo.entity import Team, MatchTeam


# TODO pflanagan: I don't like multiple inheritance here
# eventually will probably need to create a new MatchContext
# class, separate from Match

# TODO pflanagan: untangle the status, snapshot, overview mess. I think an event either
# returns a snapshot, or an overview (which is a full scorecard essentially). Can then
# also add an api to allow the client to request an overview
from scorpyo.definitions.match import MatchState


class Match(Context, Scoreable):
    def __init__(
        self,
        mse: MatchStartedEvent,
        match_engine: "MatchEngine",
        entity_registrar: "EntityRegistrar",
        command_registrar: "CommandRegistrar",
    ):
        Context.__init__(self)
        Scoreable.__init__(self)
        self.match_engine = match_engine
        self.entity_registrar = entity_registrar
        self.command_registrar = command_registrar
        self.match_id = mse.match_id
        self.start_time = mse.start_time
        self.state = MatchState.IN_PROGRESS
        self.match_type = mse.match_type
        self.home_team = mse.home_team
        self.away_team = mse.away_team
        self.home_lineup = MatchTeam(self.match_id, self.home_team)
        self.away_lineup = MatchTeam(self.match_id, self.away_team)
        self.match_inningses = []
        self.num_innings_completed = 0

        self.add_handler(EventType.INNINGS_STARTED, self.handle_innings_started)
        self.add_handler(EventType.INNINGS_COMPLETED, self.handle_innings_completed)
        self.add_handler(EventType.REGISTER_LINE_UP, self.handle_team_lineup)

    @property
    def max_bowler_overs(self) -> int:
        return self.match_type.bowler_limit

    @property
    def max_inningses(self) -> int:
        return self.match_type.innings_per_side

    @property
    def teams(self) -> List[Team]:
        return [self.home_team, self.away_team]

    @property
    def lineups(self) -> List[MatchTeam]:
        return [self.home_lineup, self.away_lineup]

    @property
    def current_innings(self) -> Optional[Innings]:
        if len(self.match_inningses) == 0:
            return None
        if len(self.match_inningses) == self.num_innings_completed:
            return None
        return self.match_inningses[-1]

    @property
    def target(self):
        if not self.current_innings:
            return None
        return self.current_innings.target

    @property
    def next_innings_target(self) -> Optional[int]:
        if self.max_inningses == 1:
            if self.num_innings_completed == 0:
                return None
            else:
                return self.innings_by_number(1)._score.total_runs + 1
        elif self.num_innings_completed < 3:
            return None
        third_innings = self.innings_by_number(3)
        next_bowling_team = third_innings.batting_team
        next_batting_team = third_innings.bowling_team
        next_batting_team_first_inn_runs = self.get_team_runs(next_batting_team, 0)
        next_bowling_team_total_runs = self.get_team_runs(next_bowling_team)
        return max(
            0, next_bowling_team_total_runs + 1 - next_batting_team_first_inn_runs
        )

    # pflanagan: should really be a property but makes testing a pain
    def max_overs(self) -> int:
        return self.match_type.overs

    def innings_by_number(self, match_innings_num: int) -> Optional[Innings]:
        # here match_innings_num is the human version i.e. starts from 1
        computer_num = match_innings_num - 1
        if computer_num >= len(self.match_inningses):
            return None
        return self.match_inningses[computer_num]

    def snapshot(self) -> dict:
        inningses_status = []
        output = {"match_id": self.match_id}
        output.update(self.overview())
        for innings in self.match_inningses:
            inningses_status.append(innings.overview())
        output["inningses"] = inningses_status
        return output

    def overview(self) -> dict:
        output = {
            "match_type": self.match_type.name,
            "start_time": self.start_time,
            "home_team": self.home_team.name,
            "away_team": self.away_team.name,
            "home_lineup": self.home_lineup(),
            "away_lineup": self.away_lineup(),
        }
        return output

    def get_lineup(self, team: Team) -> Optional[MatchTeam]:
        for lineup in self.lineups:
            if lineup.team == team:
                return lineup
        return None

    def get_team_runs(self, team: Team, innings_filter=None):
        runs = 0
        innings_count = 0
        for innings in self.match_inningses:
            if innings.batting_team == team:
                if innings_filter is not None and innings_count != innings_filter:
                    innings_count += 1
                    continue
                runs += innings()
                innings_count += 1
        return runs

    def add_innings(self, innings: Innings):
        self.match_inningses.append(innings)

    def validate(self):
        if self.num_innings_completed // 2 == self.max_inningses:
            msg = f"Match already has {self.max_inningses} innings per side"
            LOGGER.error(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        if self.num_innings_completed > 0 and not self.match_inningses[-1].is_complete:
            msg = "Previous innings has not yet ended. Please terminate first."
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)

    def handle_innings_started(self, payload: dict):
        self.validate()
        start_time = util.get_current_time()
        assert self.num_innings_completed == len(self.match_inningses)
        # index innings from 0 not 1
        match_innings_num = self.num_innings_completed
        if (
            self.current_innings
            and self.current_innings.state == InningsState.IN_PROGRESS
        ):
            msg = "cannot start an innings while another one is still in progress."
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        if not self.home_lineup or not self.away_lineup:
            msg = "cannot start an innings without first defining the lineups of each team"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        batting_team_name = payload.get("batting_team")
        if batting_team_name is None:
            LOGGER.warning("must provide batting team when starting new innings")
            raise EngineError()
        batting_team = self.entity_registrar.get_entity_data(
            EntityType.TEAM, batting_team_name
        )
        batting_lineup = self.get_lineup(batting_team)
        bowling_lineup = [
            lineup for lineup in self.lineups if lineup != batting_lineup
        ][0]
        num_prev_batting_inningses = len(
            [i for i in self.match_inningses if i.batting_team == batting_team]
        )
        ise = InningsStartedEvent(
            match_innings_num,
            num_prev_batting_inningses,
            start_time,
            batting_lineup,
            bowling_lineup,
        )
        message = self.on_innings_started(ise)
        return message

    def handle_innings_completed(self, payload: dict):
        end_time = util.get_current_time()
        try:
            reason = InningsState(payload["reason"])
        except KeyError:
            LOGGER.warning("must supply reason on InningsCompleted payload")
            raise EngineError()
        innings_id = self.current_innings.match_innings_num
        ice = InningsCompletedEvent(innings_id, end_time, reason)
        message = self.on_innings_completed(ice)
        return message

    def handle_team_lineup(self, payload: dict):
        home_or_away = payload.get("team")
        if not home_or_away or home_or_away not in ["home", "away"]:
            msg = (
                f"must specify whether team is home or away when "
                f"registering a lineup"
            )
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
        team_obj = {"home": self.home_lineup, "away": self.away_lineup}[home_or_away]
        try:
            lineup = payload["lineup"]
        except KeyError:
            msg = "must provide lineup when registering a lineup"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
        team_obj.add_lineup(
            self.entity_registrar.get_from_names(EntityType.PLAYER, payload["lineup"])
        )
        RegisterTeamLineup(team_obj.lineup)
        message = {
            "team": team_obj.team.name,
            "home_or_away": home_or_away,
            "lineup": team_obj(),
        }
        return message

    @record_command
    def on_innings_started(self, ise: InningsStartedEvent):
        new_innings = Innings(ise, self, self.entity_registrar, self.command_registrar)
        new_innings.target = self.next_innings_target
        self.add_innings(new_innings)
        self._child_context = new_innings
        return self.current_innings.description()

    @record_command
    def on_innings_completed(self, ice: InningsCompletedEvent):
        innings = self.current_innings
        if not innings:
            LOGGER.warning(
                f"cannot complete an innings when there are no existing " f"inningses"
            )
            raise EngineError()
        if self.current_innings.state != InningsState.IN_PROGRESS:
            msg = (
                f"innings {innings.match_innings_num} is not in "
                f"progress so cannot complete it"
            )
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        if innings.match_innings_num != ice.match_innings_num:
            msg = (
                f"the innings number of the InningsCompletedEvent does "
                f"not match the current_innings number"
            )
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
        innings.terminate(ice)
        self.num_innings_completed += 1
        return innings.overview()

    def on_ball_completed(self, bce: BallCompletedEvent):
        super().update_score(bce)
        return self.current_innings.on_ball_completed(bce)

    def on_batter_innings_completed(self, bic: BatterInningsCompletedEvent):
        return self.current_innings.on_batter_innings_completed(bic)

    def on_batter_innings_started(self, bis: BatterInningsStartedEvent):
        return self.current_innings.on_batter_innings_started(bis)
