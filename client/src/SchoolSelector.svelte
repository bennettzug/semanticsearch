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
            shortName: "UW",
            longName: "University of Washington",
            accentColor: "#4B2E83",
        },
        {
            shortName: "UMD",
            longName: "University of Maryland",
            accentColor: "#FFD200",
        },
        {
            shortName: "UCLA",
            longName: "University of California Los Angeles",
            accentColor: "#2D68C4",
        },
        {
            shortName: "UT",
            longName: "University of Texas",
            accentColor: "#BF5700",
        },
        {
            shortName: "UCB",
            longName: "University of California Berkeley",
            accentColor: "#FDB515",
        },
        {
            shortName: "USC",
            longName: "University of Southern California",
            accentColor: "#990000",
        },
        {
            shortName: "NYU",
            longName: "New York University",
            accentColor: "#57068C",
        },
        {
            shortName: "MIT",
            longName: "Massachusetts Institute of Technology",
            accentColor: "#A31F34",
        },
        {
            shortName: "YALE",
            longName: "Yale University",
            accentColor: "#00356B",
        },
        {
            shortName: "HARV",
            longName: "Harvard University",
            accentColor: "#A51C30",
        },
        {
            shortName: "STAN",
            longName: "Stanford University",
            accentColor: "#8C1515",
        },
        {
            shortName: "CORN",
            longName: "Cornell University",
            accentColor: "#B31B1B",
        },
        {
            shortName: "DUKE",
            longName: "Duke University",
            accentColor: "#003366",
        },
        {
            shortName: "GT",
            longName: "Georgia Tech",
            accentColor: "#C99700",
        },
        {
            shortName: "UMICH",
            longName: "University of Michigan",
            accentColor: "#FFCB05",
        },
        {
            shortName: "UVA",
            longName: "University of Virginia",
            accentColor: "#F84C1E",
        },
        {
            shortName: "UNC",
            longName: "University of North Carolina",
            accentColor: "#7BAFD4",
        },
        {
            shortName: "UWISC",
            longName: "University of Wisconsin Madison",
            accentColor: "#C5050C",
        },
        {
            shortname: "HOWARD",
            longName: "Howard University",
            accentColor: "#8C1515",
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
