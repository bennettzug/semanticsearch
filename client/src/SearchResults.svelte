<script>
    import { sendSearchRequest } from "./utils/searchService";
    import { onMount, afterUpdate } from "svelte";
    import { writable } from "svelte/store";

    let query = "";
    let selectedCollege = ""; // Assuming you have a way to set this value

    let searchResults = writable([]); // Make searchResults reactive

    async function search() {
        const response = await sendSearchRequest(query, selectedCollege);
        searchResults.set(response);
    }

    // Call search whenever query or selectedCollege changes
</script>

<main>
    <!-- Your Svelte component UI here -->
    <div id="searchResults" class="mt-3">
        {#each $searchResults as course}
            <div class="course">
                <p><strong>{course[0]} {course[1]}: {course[2]}</strong></p>
                <p>{course[3]}</p>
                <p><i>{course[4]} hour(s).</i></p>
            </div>
        {/each}
    </div>
</main>
