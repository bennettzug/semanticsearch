<script>
    import { sendSearchRequest } from "./utils/searchService";
    import { writable } from "svelte/store";
    export let selectedCollege = null;

    let query = "";
    let searchResults = writable([]);

    async function search() {
        // Call the search function with the query
        const results = await sendSearchRequest(query, selectedCollege);
        searchResults.set(results);
    }

    function handleKeyup(event) {
        if (event.key === "Enter") {
            search();
        }
    }
</script>

<div class="search-bar">
    <div class="search-wrapper">
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <span class="search-icon" on:click={search}>
            <svg
                width="22"
                height="22"
                viewBox="0 0 22 22"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
            >
                <path
                    d="M20.2928 21.7071C20.6833 22.0976 21.3165 22.0976 21.707 21.7071C22.0976 21.3166 22.0976 20.6834 21.707 20.2929L20.2928 21.7071ZM17.7778 9.88889C17.7778 14.2458 14.2458 17.7778 9.88889 17.7778V19.7778C15.3504 19.7778 19.7778 15.3504 19.7778 9.88889H17.7778ZM9.88889 17.7778C5.53198 17.7778 2 14.2458 2 9.88889H0C0 15.3504 4.42741 19.7778 9.88889 19.7778V17.7778ZM2 9.88889C2 5.53198 5.53198 2 9.88889 2V0C4.42741 0 0 4.42741 0 9.88889H2ZM9.88889 2C14.2458 2 17.7778 5.53198 17.7778 9.88889H19.7778C19.7778 4.42741 15.3504 0 9.88889 0V2ZM14.7373 16.1516L20.2928 21.7071L21.707 20.2929L16.1515 14.7373L14.7373 16.1516Z"
                    fill="#CACACA"
                />
            </svg>
        </span>
        <input
            type="text"
            class="search-input form-control mb-2"
            placeholder="search something..."
            bind:value={query}
            on:keyup={handleKeyup}
        />
    </div>
</div>

{#if $searchResults.length === 0}
    <div class="default-message">
        <p>Search for courses with an AI based semantic search.</p>
        <p>
            We search courses by their meaning, not exact keywords. Try
            something like "cooking and chemistry", or "<span class="misspelled"
                >mathamatics</span
            >."
        </p>
    </div>
{:else}
    <div id="searchResults" class="mt-3">
        {#each $searchResults as course}
            <div class="course">
                <p><strong>{course[0]} {course[1]}: {course[2]}</strong></p>
                <p>{course[3]}</p>
                <p><i>{course[4]} hour(s).</i></p>
            </div>
        {/each}
    </div>
{/if}
