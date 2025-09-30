const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function resolveEndpoint(path) {
    return `${API_BASE_URL}${path}` || path;
}

export async function sendSearchRequest(query, selectedCollege) {
    const trimmedQuery = query.trim();

    if (!trimmedQuery || !selectedCollege) {
        return [];
    }

    const response = await fetch(resolveEndpoint("/search"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify({
            query: trimmedQuery,
            school: selectedCollege,
        }),
    });

    let payload;
    if (!response.ok) {
        try {
            payload = await response.json();
        } catch (error) {
            payload = null;
        }

        const message =
            payload?.error || `Search request failed with status ${response.status}`;
        const detail = payload?.detail ? `: ${payload.detail}` : "";
        throw new Error(`${message}${detail}`);
    }

    payload = await response.json();

    if (Array.isArray(payload)) {
        return payload;
    }

    if (payload && Array.isArray(payload.results)) {
        return payload.results;
    }

    throw new Error("Unexpected response format from the search endpoint.");
}
