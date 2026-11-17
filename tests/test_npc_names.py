from game.npc_names import NPC_NAMES


def test_npc_names_keep_their_content_and_pick_order() -> None:
    assert NPC_NAMES == ("Bob", "Paul", "Thomas", "Marie", "Sam", "Lisa")
