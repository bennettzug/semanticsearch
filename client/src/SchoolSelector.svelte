<script>
    import { createEventDispatcher } from "svelte";

    const dispatch = createEventDispatcher();

    const schools = [
        {
            shortName: "UIUC",
            longName: "University of Illinois Urbana-Champaign",
            accentColor: "#FF5F0F",
        },
        {
            shortName: "ASU",
            longName: "Appalachian State University",
            accentColor: "#FFCC00",
        },
        {
            shortName: "NCSU",
            longName: "North Carolina State University",
            accentColor: "#CC0000",
        },
        {
            shortName: "UNC",
            longName: "University of North Carolina",
            accentColor: "#7BAFD4",
        },
    ];

    function selectSchool(school) {
        dispatch("schoolSelected", school);
    }
</script>

<div class="college-selector">
    <div class="college-buttons">
        {#each schools as school}
            <button
                class="college-btn"
                style="background-color: {school.accentColor}"
                on:click={() => selectSchool(school)}
            >
                {school.longName}
            </button>
        {/each}
    </div>
</div>
