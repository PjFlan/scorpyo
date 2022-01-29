import enum
from typing import Optional, List

import scorpyo.util as util
from scorpyo.context import Context
from scorpyo.events import (
    BallCompletedEvent,
    BatterInningsCompletedEvent,
    InningsStartedEvent,
    BatterInningsStartedEvent,
    MatchStartedEvent,
    EventType,
    InningsCompletedEvent,
)
from scorpyo.entity import EntityType
from scorpyo.innings import Innings, InningsState
from scorpyo.score import Scoreable
from scorpyo.team import Team, MatchTeam


# TODO pflanagan: I don't like multiple inheritance here
# eventually will probably need to create a new MatchContext
# class, separate from Match
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
    def max_overs(self) -> int:
        return self.match_type.overs

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
        return self.match_inningses[-1]

    @property
    def target(self) -> Optional[int]:
        if self.match_type.innings_per_side == 1:
            if self.num_innings_completed == 0:
                return None
            else:
                return self.match_inningses[0]() + 1
        elif self.num_innings_completed < 3:
            return None
        bowling_team = self.current_innings.bowling_team
        batting_team = self.current_innings.batting_team
        if len(self.match_inningses) == 3:
            # PF: if we have not yet started the 4th innings we need to make sure
            # we preempt who will be the batting and bowling teams
            bowling_team = (
                self.current_innings.batting_team
                if len(self.match_inningses) == 3
                else bowling_team
            )
            batting_team = (
                self.current_innings.bowling_team
                if len(self.match_inningses) == 3
                else batting_team
            )
        batting_team_first_inn_runs = self.get_team_runs(batting_team, 0)
        bowling_team_total_runs = self.get_team_runs(bowling_team)
        return max(0, bowling_team_total_runs + 1 - batting_team_first_inn_runs)

    @property
    def runs_to_win(self) -> Optional[int]:
        if self.target is None:
            return None
        if self.target <= 0:
            return 0
        if self.match_type.innings_per_side == 2 and len(self.match_inningses) == 3:
            return self.target
        return max(0, self.target - self.current_innings.total_runs)

    @property
    def target_reached(self) -> bool:
        if self.runs_to_win is None:
            return False
        return self.runs_to_win == 0

    def status(self):
        for i, innings in enumerate(self.match_inningses):
            print(f"innings {i}: {innings.status()}\n")

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
        # index innings from 0 not 1
        innings_num = self.num_innings_completed
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
        if opening_bowler not in bowling_lineup:
            raise ValueError(
                f"no bowler in bowling team {bowling_lineup.name} with "
                f"name {opening_bowler.name}"
            )
        ise = InningsStartedEvent(
            innings_num,
            start_time,
            batting_lineup,
            bowling_lineup,
            opening_bowler,
        )
        self.on_innings_started(ise)
        return ise

    def handle_innings_completed(self, payload: dict):
        end_time = util.get_current_time()
        reason = InningsState(payload["reason"])
        innings_id = payload["innings_num"]
        ice = InningsCompletedEvent(innings_id, end_time, reason)
        self.on_innings_completed(ice)
        return ice

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

    def on_innings_started(self, ise: InningsStartedEvent):
        new_innings = Innings(ise, self)
        self.add_innings(new_innings)
        self._child_context = new_innings

    def on_innings_completed(self, ice: InningsCompletedEvent):
        current_innings = self.current_innings
        if not current_innings:
            raise ValueError(
                f"cannot complete an innings when there are no existing " f"inningses"
            )
        if self.current_innings.state != InningsState.IN_PROGRESS:
            raise ValueError(
                f"innings {current_innings.innings_num} is not in "
                f"progress so cannot complete it"
            )
        if current_innings.innings_num != ice.innings_num:
            raise ValueError(
                f"the innings number of the InningsCompletedEvent does "
                f"not match the current_innings number"
            )
        self.num_innings_completed += 1
        self.current_innings.on_innings_completed(ice)

    def on_ball_completed(self, bce: BallCompletedEvent):
        super().update_score(bce)
        self.current_innings.on_ball_completed(bce)

    def on_batter_innings_completed(self, bic: BatterInningsCompletedEvent):
        self.current_innings.on_batter_innings_completed(bic)

    def on_batter_innings_started(self, bis: BatterInningsStartedEvent):
        self.current_innings.on_batter_innings_started(bis)


class MatchState(enum.Enum):
    COMPLETED = 0
    RAINED_OFF = 1
    IN_PROGRESS = 2
