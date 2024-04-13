function sendSearchRequest(query, selectedCollege) {
    const trimmedQuery = query.trim();
    if (!trimmedQuery || !selectedCollege) {
        document.getElementById('searchResults').innerHTML = '';
        return;
    }

    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: trimmedQuery, school: selectedCollege })
    })
        .then(response => response.json())
        .then(data => displayResults(data))
        .catch(error => console.error('Error:', error));
}

function displayResults(results) {
    let resultHtml = "";
    results.forEach(function (course) {
        resultHtml += "<div class='course'>";
        resultHtml += `<p><strong>${course[0]} ${course[1]}: ${course[2]}</strong></p>`;
        resultHtml += `<p>${course[3]}</p>`;
        resultHtml += `<p><i>${course[4]} hour(s).</i></p>`;
        resultHtml += "</div>";
    });
    document.getElementById('searchResults').innerHTML = resultHtml;
}

const schools = {
    'UIUC': {
        shortName: 'UIUC',
        longName: 'University of Illinois Urbana-Champaign',
        accentColor: '#FF5F0F'
    },
    'UCLA': {
        shortName: 'UCLA',
        longName: 'University of California, Los Angeles',
        accentColor: '#0070C0'
    },
    'Stanford': {
        shortName: 'Stanford',
        longName: 'Stanford University',
        accentColor: '#8C1515'
    },
    'ASU': {
        shortName: 'ASU',
        longName: 'Appalachian State University',
        accentColor: '#FFCC00'
    }
};

