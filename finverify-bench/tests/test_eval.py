import json

from benchmark.evaluator import evaluate, print_report

with open("data/seed_50.json", "r") as f:
    dataset = json.load(f)

predictions = []

for sample in dataset:
    predictions.append({
        "id": sample["id"],
        "prediction": sample["ground_truth"]
    })

report = evaluate(dataset, predictions)

print_report(report)