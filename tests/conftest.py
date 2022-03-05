import os
from copy import deepcopy

import pytest

from scorpyo import entity
from scorpyo.engine import MatchEngine
from scorpyo.innings import find_innings, BatterInningsState
from scorpyo.match import Match
from scorpyo.over import OverState
from scorpyo.entity import Player
from scorpyo.registrar import EntityType, EntityRegistrar, EventRegistrar
from scorpyo.static_data import match
from scorpyo.entity import MatchTeam
from .common import RESOURCES_PATH, TEST_CONFIG
from .resources import HOME_TEAM, AWAY_TEAM, HOME_PLAYERS, AWAY_PLAYERS


# TODO: maybe these player names should be enums
test_players_home = HOME_PLAYERS
test_players_away = AWAY_PLAYERS
test_team_home = HOME_TEAM
test_team_away = AWAY_TEAM


# noinspection PyMissingConstructor
class MockMatch(Match):
    def __init__(
        self, entity_registrar: EntityRegistrar, event_registrar: EventRegistrar
    ):
        self.entity_registrar = entity_registrar
        self.event_registrar = event_registrar
        self.match_id = 12345
        self.num_innings_completed = 0
        self.match_inningses = []
        self.match_type = match.TWENTY_20

    def swap_batters(self, old_batter, new_batter):
        existing_innings = find_innings(
            old_batter, self.current_innings.batter_inningses
        )
        new_innings = deepcopy(existing_innings)
        new_innings.batting_state = BatterInningsState.IN_PROGRESS
        existing_innings.batting_state = BatterInningsState.DISMISSED
        new_innings.player = new_batter
        self.current_innings.batter_inningses.append(new_innings)
        if self.current_innings.on_strike_innings.player == old_batter:
            self.current_innings.on_strike_innings = new_innings
        else:
            self.current_innings.off_strike_innings = new_innings

    def apply_over(self, bowler: Player):
        prev_over = self.current_innings.overs[-1]
        if prev_over.state != OverState.IN_PROGRESS:
            next_over = deepcopy(prev_over)
            next_over.state = OverState.IN_PROGRESS
            next_over.bowler = bowler
            self.current_innings.overs.append(next_over)
            next_over.state = OverState.COMPLETED
            next_over.number = prev_over.number + 1
        else:
            payload = {"score_text": "."}
            self.current_innings.current_over.bowler = bowler
            for _ in range(6):
                self.current_innings.handle_ball_completed(payload)
            oc_payload = {
                "over_num": 0,
                "bowler": bowler.name,
                "reason": OverState.COMPLETED,
            }
            self.current_innings.handle_over_completed(oc_payload)

    def apply_overs(self, num_overs) -> Player:
        bowling_lineup = self.current_innings.bowling_lineup
        next_idx = 0
        for over in range(num_overs):
            next_idx = over % len(bowling_lineup)
            next_bowler = bowling_lineup[next_idx]
            self.apply_over(next_bowler)
        next_bowler = bowling_lineup[(next_idx + 1) % len(bowling_lineup)]
        return next_bowler


@pytest.fixture()
def registrar():
    ent_registrar = EntityRegistrar(TEST_CONFIG)
    return ent_registrar


@pytest.fixture()
def mock_engine(registrar):
    return MatchEngine(registrar)


@pytest.fixture()
def mock_match(registrar):
    mock_match = MockMatch(registrar, EventRegistrar())
    teams = registrar.get_all_of_type(EntityType.TEAM)
    mock_match.home_team = teams[0]
    mock_match.away_team = teams[1]
    mock_match.home_lineup = MatchTeam(mock_match.match_id, mock_match.home_team)
    mock_match.away_lineup = MatchTeam(mock_match.match_id, mock_match.away_team)
    lineup_home = registrar.get_from_names(EntityType.PLAYER, test_players_home)
    lineup_away = registrar.get_from_names(EntityType.PLAYER, test_players_away)
    mock_match.home_lineup.add_lineup(lineup_home)
    mock_match.away_lineup.add_lineup(lineup_away)
    return mock_match


@pytest.fixture()
def mock_innings(mock_match: MockMatch):
    bowler_name = test_players_away[-1]
    payload = {"batting_team": test_team_home, "opening_bowler": bowler_name}
    mock_match.handle_innings_started(payload)
    return mock_match.current_innings
