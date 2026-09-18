from dreamnet.environment import NetworkEnvironment
from dreamnet.policy import baseline_policy
from dreamnet.replay import replay_tree, score_result
from dreamnet.rollout import online_rollout


def test_online_tree_has_one_primary_parent_and_valid_children():
    env = NetworkEnvironment(seed=1)
    incident = env.generate_incidents(1, "unit")[0]
    result = online_rollout(incident, env, baseline_policy())
    tree = result.tree
    assert len(tree.nodes) > 1
    for node_id, node in tree.nodes.items():
        if node_id != tree.ROOT_ID:
            assert node.parent_id in tree.nodes
            assert node_id in tree.children[node.parent_id]


def test_replay_only_reveals_recorded_nodes():
    env = NetworkEnvironment(seed=2)
    incident = env.generate_incidents(1, "unit")[0]
    online = online_rollout(incident, env, baseline_policy())
    replay = replay_tree(online.tree, baseline_policy())
    assert replay.revealed <= set(online.tree.nodes)
    assert score_result(replay).requests <= score_result(online).requests


def test_same_seed_is_reproducible():
    left = NetworkEnvironment(seed=9).generate_incidents(10, "x")
    right = NetworkEnvironment(seed=9).generate_incidents(10, "x")
    assert left == right
