from measurement_engine import run_test


result = run_test(
    server_id="server_01",
    host="10.113.250.227",
    port=5001,
    duration_sec=5,
    streams=4,
    ramp_up_sec=2
)

print()
print("RESULT DICTIONARY")
print(result)