from dreamnet.environment import NetworkEnvironment
from dreamnet.optimizer import evaluate_policy, optimize_policy
from dreamnet.policy import baseline_policy
from dreamnet.rollout import online_rollout


def test_optimizer_never_selects_worse_replay_policy():
    env = NetworkEnvironment(seed=5)
    incidents = env.generate_incidents(20, "train")
    trees = [online_rollout(i, env, baseline_policy()).tree for i in incidents]
    baseline_value, _ = evaluate_policy(baseline_policy(), trees)
    learned, _ = optimize_policy(baseline_policy(), trees, candidates=40, seed=6)
    learned_value, _ = evaluate_policy(learned, trees)
    assert learned_value >= baseline_value
