function search() {
    var query = document.getElementById('searchInput').value;
    var school = document.getElementById('school').value;
    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: query, school: school })
    })
        .then(response => response.json())
        .then(data => displayResults(data))
        .catch(error => console.error('Error:', error));
}

function displayResults(results) {
    var resultHtml = "";
    results.forEach(function (course) {
        resultHtml += "<div class='course'>";
        resultHtml += "<p><strong>" + course[0] + " " + course[1] + ": " + course[2] + "</strong></p>"; // Assuming the course code is at index 0
        resultHtml += "<p>" + course[3] + "</p>"; // Assuming the course description is at index 3
        resultHtml += "<p><i>" + course[4] + " hour(s).</i></p>"; // Assuming the hours info is at index 4
        resultHtml += "</div>"; // Wrap each course in a div
    });
    document.getElementById('searchResults').innerHTML = resultHtml;
}
