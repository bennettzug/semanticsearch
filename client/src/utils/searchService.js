// src/utils/searchService.js
export function sendSearchRequest(query, selectedCollege) {
    const trimmedQuery = query.trim();
    if (!trimmedQuery || !selectedCollege) {
        return Promise.resolve([]);
    }

    return fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: trimmedQuery, school: selectedCollege })
    })
        .then(response => response.json())
        .catch(error => {
            console.error('Error:', error);
            return [];
        });
}