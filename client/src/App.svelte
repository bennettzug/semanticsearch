<script>
    import SchoolSelector from "./SchoolSelector.svelte";
    import SearchBar from "./SearchBar.svelte";
    import SearchResults from "./SearchResults.svelte";

    let selectedSchool = null;

    function handleSchoolSelection(event) {
        selectedSchool = event.detail;
    }
    function changeSchool() {
        selectedSchool = null;
    }
</script>

<head>
    <title>Course Search</title>
    <link rel="icon" type="image/svg+xml" href="assets/search.svg" />
</head>

<main>
    {#if !selectedSchool}
        <SchoolSelector on:schoolSelected={handleSchoolSelection} />
    {/if}

    {#if selectedSchool}
        <div id="schoolchange">
            <h1 style="color: {selectedSchool.accentColor}">
                {selectedSchool.longName}
            </h1>
            <!-- svelte-ignore a11y-invalid-attribute -->
            <a
                href="javascript:void(0);"
                class="change-school"
                on:click={changeSchool}
            >
                Change Schools?
            </a>
        </div>
        <SearchBar selectedCollege={selectedSchool.shortName} />
        <SearchResults />
    {/if}
</main>

<style>
    @import url("https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap");
</style>
