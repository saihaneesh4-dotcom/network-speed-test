from database import save_result, get_results

save_result(
    "server_02",
    12.5,
    1.4,
    0.0,
    96.8,
    43.2,
    4,
    10,
    "2026-09-04 22:57:00"
)

results = get_results()

for result in results:
    print(result)