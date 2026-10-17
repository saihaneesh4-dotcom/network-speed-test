async function startTest() {

    const button = document.getElementById("startBtn");
    const status = document.getElementById("status");

    button.disabled = true;
    status.innerText = "Selecting best server...";

    document.getElementById("download").innerText = "--";
    document.getElementById("upload").innerText = "--";
    document.getElementById("latency").innerText = "--";
    document.getElementById("jitter").innerText = "--";
    document.getElementById("loss").innerText = "--";
    document.getElementById("server").innerText = "--";

    try {

        status.innerText = "Running speed test...";

        const response = await fetch(
            "http://127.0.0.1:5000/start-test",
            {
                method: "POST"
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message);
        }

        document.getElementById("download").innerText =
            Number(data.download_mbps).toFixed(2);

        document.getElementById("upload").innerText =
            Number(data.upload_mbps).toFixed(2);

        document.getElementById("latency").innerText =
            Number(data.latency_ms).toFixed(2);

        document.getElementById("jitter").innerText =
            Number(data.jitter_ms).toFixed(2);

        document.getElementById("loss").innerText =
            Number(data.packet_loss_percent).toFixed(2);

        document.getElementById("server").innerText =
            data.server_id;

        status.innerText = "Test completed";

    } catch (error) {

        status.innerText = "Test failed: " + error.message;

    }

    button.disabled = false;
}
