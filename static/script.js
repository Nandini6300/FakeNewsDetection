
let requestInProgress = false;


async function checkNews() {

    const newsInput = document.getElementById("newsInput");

    const button = document.getElementById("checkButton");

    const loading = document.getElementById("loading");

    const resultSection = document.getElementById("resultSection");

    const errorBox = document.getElementById("errorBox");

    const news = newsInput.value.trim();

    if (!news) {

        alert("Please enter some news.");

        return;
    }

    if (requestInProgress) {
        return;
    }

    requestInProgress = true;

    resultSection.classList.add("hidden");

    errorBox.classList.add("hidden");

    loading.classList.remove("hidden");

    button.disabled = true;

    button.textContent = "Analyzing...";

    try {

        const response = await fetch("/api/check", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                news: news
            })

        });

        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.error || "Unable to verify news."
            );

        }

        // Input news

        document.getElementById("inputNews").textContent =
            data.input_news || news;

        // Prediction

        const prediction =
            data.prediction || "FAKE";

        const predictionBox =
            document.getElementById("prediction");

        predictionBox.textContent = prediction;

        predictionBox.className = "prediction";

        if (prediction === "FAKE") {

            predictionBox.classList.add("fake");

        } else {

            predictionBox.classList.add("real");

        }

        // Explanation

        document.getElementById("explanation").textContent =
            data.explanation || "No explanation available.";

        // Evidence

        displayEvidence(
            "supportingEvidence",
            data.supporting_evidence || []
        );

        displayEvidence(
            "contradictingEvidence",
            data.contradicting_evidence || []
        );

        // Sources

        displaySources(data.sources || []);

        // Article count

        document.getElementById("articleCount").textContent =
            "Relevant articles extracted: " +
            (data.articles_found ?? 0);

        // Processing time

        document.getElementById("processingTime").textContent =
            "Processing time: " +
            (data.processing_time ?? 0) +
            " seconds";

        // Show results

        resultSection.classList.remove("hidden");

        resultSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }

    catch (error) {

        errorBox.textContent = error.message;

        errorBox.classList.remove("hidden");

    }

    finally {

        loading.classList.add("hidden");

        button.disabled = false;

        button.textContent = "Analyze News";

        requestInProgress = false;

    }

}


function displayEvidence(elementId, evidence) {

    const container = document.getElementById(elementId);

    container.replaceChildren();

    if (!evidence.length) {

        const message = document.createElement("p");

        message.textContent = "No evidence identified.";

        container.appendChild(message);

        return;
    }

    evidence.forEach(item => {

        const div = document.createElement("div");

        div.className = "evidence-item";

        div.textContent =
            (item.source_id || "") +
            " - " +
            (item.reason || "");

        container.appendChild(div);

    });

}


function displaySources(sources) {

    const container = document.getElementById("sources");

    container.replaceChildren();

    if (!sources.length) {

        const message = document.createElement("p");

        message.textContent =
            "No verified source references available.";

        container.appendChild(message);

        return;
    }

    sources.forEach(source => {

        try {

            const parsedURL = new URL(source.url);

            if (
                parsedURL.protocol !== "https:" &&
                parsedURL.protocol !== "http:"
            ) {
                return;
            }

            const div = document.createElement("div");

            div.className = "source-item";

            const title = document.createElement("p");

            title.textContent =
                source.title || "News article";

            const link = document.createElement("a");

            link.href = parsedURL.href;

            link.textContent =
                "Visit source: " +
                (source.domain || "Website");

            link.target = "_blank";

            link.rel = "noopener noreferrer";

            div.appendChild(title);

            div.appendChild(link);

            container.appendChild(div);

        }

        catch (error) {

            console.log("Invalid source URL:", error);

        }

    });

}
