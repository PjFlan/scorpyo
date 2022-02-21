import enum
from typing import Optional, List

import scorpyo.util as util
from scorpyo.context import Context, record_event
from scorpyo.events import (
    BallCompletedEvent,
    BatterInningsCompletedEvent,
    InningsStartedEvent,
    BatterInningsStartedEvent,
    MatchStartedEvent,
    EventType,
    InningsCompletedEvent,
    RegisterTeamLineup,
)
from scorpyo.entity import EntityType
from scorpyo.innings import Innings, InningsState
from scorpyo.score import Scoreable
from scorpyo.team import Team, MatchTeam


# TODO pflanagan: I don't like multiple inheritance here
# eventually will probably need to create a new MatchContext
# class, separate from Match

# TODO pflanagan: untangle the status, snapshot, overview mess. I think an event either
# returns a snapshot, or an overview (which is a full scorecard essentially). Can then
# also add an api to allow the client to request an overview
class Match(Context, Scoreable):
    def __init__(self, mse: MatchStartedEvent, match_engine: "MatchEngine"):
        Context.__init__(self)
        Scoreable.__init__(self)
        self.match_engine = match_engine
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

    def status(self) -> dict:
        inningses_status = []
        output = {"match_id": self.match_id, "snapshot": self.snapshot()}
        for innings in enumerate(self.match_inningses):
            inningses_status.append(innings.status())
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

    def snapshot(self):
        return ""

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
        if len(self.match_inningses) == self.max_inningses:
            raise ValueError(f"Match already has {self.max_inningses} innings")
        if len(self.match_inningses) > 0 and not self.match_inningses[-1].is_complete:
            raise ValueError("Previous innings has not yet ended.")

    def handle_innings_started(self, payload: dict):
        start_time = util.get_current_time()
        assert self.num_innings_completed == len(self.match_inningses)
        # index innings from 0 not 1
        match_innings_num = self.num_innings_completed
        if (
            self.current_innings
            and self.current_innings.state == InningsState.IN_PROGRESS
        ):
            raise ValueError(
                "cannot start an innings while another one is still in progress."
            )
        if not self.home_lineup or not self.away_lineup:
            raise ValueError(
                "cannot start an innings without first defining the "
                "lineups of each team"
            )
        batting_team_name = payload.get("batting_team")
        if not batting_team_name:
            raise ValueError("must provide batting team when starting new innings")
        batting_team = self.entity_registrar.get_entity_data(
            EntityType.TEAM, batting_team_name
        )
        batting_lineup = self.get_lineup(batting_team)
        bowling_lineup = [
            lineup for lineup in self.lineups if lineup != batting_lineup
        ][0]
        opening_bowler = self.entity_registrar.get_entity_data(
            EntityType.PLAYER, payload["opening_bowler"]
        )
        num_prev_batting_inningses = len(
            [i for i in self.match_inningses if i.batting_team == batting_team]
        )
        if opening_bowler not in bowling_lineup:
            raise ValueError(
                f"no bowler in bowling team {bowling_lineup.name} with "
                f"name {opening_bowler.name}"
            )
        ise = InningsStartedEvent(
            match_innings_num,
            num_prev_batting_inningses,
            start_time,
            batting_lineup,
            bowling_lineup,
            opening_bowler,
        )
        message = self.on_innings_started(ise)
        return message

    def handle_innings_completed(self, payload: dict):
        end_time = util.get_current_time()
        reason = InningsState(payload["reason"])
        innings_id = payload["match_innings_num"]
        ice = InningsCompletedEvent(innings_id, end_time, reason)
        message = self.on_innings_completed(ice)
        return message

    def handle_team_lineup(self, payload: dict):
        home_or_away = payload.get("team")
        if not home_or_away or home_or_away not in ["home", "away"]:
            raise ValueError(
                f"must specify whether team is home or away when "
                f"registering a lineup"
            )
        team_obj = {"home": self.home_lineup, "away": self.away_lineup}[home_or_away]
        lineup = payload.get("lineup")
        if not lineup:
            raise ValueError("must provide lineup when registering a lineup")
        team_obj.add_lineup(
            self.entity_registrar.get_from_names(EntityType.PLAYER, payload["lineup"])
        )
        rlu = RegisterTeamLineup(team_obj.lineup)
        message = {
            "team": team_obj.team.name,
            "home_or_away": home_or_away,
            "lineup": team_obj(),
        }
        return message

    @record_event
    def on_innings_started(self, ise: InningsStartedEvent):
        new_innings = Innings(ise, self)
        new_innings.target = self.next_innings_target
        self.add_innings(new_innings)
        self._child_context = new_innings
        return self.current_innings.description()

    @record_event
    def on_innings_completed(self, ice: InningsCompletedEvent):
        innings = self.current_innings
        if not innings:
            raise ValueError(
                f"cannot complete an innings when there are no existing " f"inningses"
            )
        if self.current_innings.state != InningsState.IN_PROGRESS:
            raise ValueError(
                f"innings {innings.match_innings_num} is not in "
                f"progress so cannot complete it"
            )
        if innings.match_innings_num != ice.match_innings_num:
            raise ValueError(
                f"the innings number of the InningsCompletedEvent does "
                f"not match the current_innings number"
            )
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


class MatchState(enum.Enum):
    COMPLETED = 0
    RAINED_OFF = 1
    IN_PROGRESS = 2
