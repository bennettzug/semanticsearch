<script>
    import { sendSearchRequest } from "./utils/searchService";
    import { searchStore } from "./lib/stores/searchStore";

    export let selectedCollege = null;

    let query = "";
    let previousCollege = null;
    let schoolSelected = false;

    $: if (selectedCollege !== previousCollege) {
        previousCollege = selectedCollege;
        if (!selectedCollege) {
            query = "";
        }
        searchStore.reset();
    }

    $: schoolSelected = Boolean(selectedCollege);

    async function search() {
        const trimmedQuery = query.trim();
        const schoolCode = selectedCollege ? selectedCollege.toUpperCase() : null;

        if (!schoolSelected || trimmedQuery.length === 0) {
            searchStore.reset();
            return;
        }

        searchStore.start(trimmedQuery, schoolCode);

        try {
            const results = await sendSearchRequest(trimmedQuery, selectedCollege);
            searchStore.succeed(trimmedQuery, schoolCode, results);
        } catch (error) {
            console.error("Semantic search request failed", error);
            const message = error instanceof Error ? error.message : "Unable to fetch results.";
            searchStore.fail(trimmedQuery, schoolCode, message);
        }
    }

    function handleInput(event) {
        query = event.currentTarget.value;
        if (query.trim().length === 0) {
            searchStore.reset();
        }
    }
</script>

<div class="search-bar">
    <form class="search-wrapper" on:submit|preventDefault={search}>
        <button type="submit" class="search-icon" aria-label="Submit search" disabled={!schoolSelected}>
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
        </button>
        <input
            type="text"
            class="search-input form-control mb-2"
            placeholder="Search courses..."
            bind:value={query}
            on:input={handleInput}
            disabled={!schoolSelected}
        />
    </form>
</div>
