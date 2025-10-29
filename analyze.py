import pandas as pd

data = pd.read_pickle("log/2025-10-29_01-12-54-858255/__session__/15/0_direct_exp_gen")
hypothesis, sota_exp = data.trace.get_sota_hypothesis_and_experiment()
sota_result = sota_exp.result
print("SOTA results:")
print(sota_result)
print("SOTA factors:")
for prev_exp in sota_exp.based_experiments:
    for sub_task in prev_exp.sub_tasks:
        print(sub_task.factor_name)
        print("..", sub_task.factor_formulation)

for sub_task in sota_exp.sub_tasks:
    print(sub_task.factor_name)
    print("..", sub_task.factor_formulation)