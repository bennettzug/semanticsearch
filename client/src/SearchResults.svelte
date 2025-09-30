<script>
    import { derived } from "svelte/store";
    import { searchStore } from "./lib/stores/searchStore";
    import { SCHOOLS } from "./data/schools";

    const normalizedResults = derived(searchStore, ($store) => {
        if (!Array.isArray($store.results)) {
            return [];
        }

        return $store.results.map((course) => {
            if (Array.isArray(course)) {
                const [subject, number, name, description, creditHours, similarity] = course;
                return {
                    school: "",
                    schoolColor: "#4b5563",
                    subject,
                    number,
                    name,
                    description,
                    creditHours,
                    similarity,
                };
            }

            const school = (course?.school ?? "").toUpperCase();
            const schoolMeta = SCHOOLS.find(
                (entry) => entry.shortName.toUpperCase() === school
            );

            return {
                school,
                schoolColor: schoolMeta?.accentColor ?? "#4b5563",
                subject: course?.subject ?? "",
                number: course?.number ?? "",
                name: course?.name ?? "",
                description: course?.description ?? "",
                creditHours: course?.creditHours ?? "",
                similarity: course?.similarity ?? null,
            };
        });
    });
</script>

<main>
    {#if $searchStore.status === "idle"}
        <div class="default-message">
            <p>Search for courses with an AI semantic search.</p>
            <p>
                Results focus on meaning, so try creative prompts like
                <span class="example">"cooking and chemistry"</span> or
                <span class="example">"intro to product design"</span>.
            </p>
        </div>
    {:else if $searchStore.status === "loading"}
        <div class="loading">Finding relevant courses…</div>
    {:else if $searchStore.status === "error"}
        <div class="error">
            <p>We hit a snag while searching.</p>
            <p class="error-detail">{$searchStore.error}</p>
        </div>
    {:else if $searchStore.results.length === 0}
        <div class="empty-state">No courses matched that description.</div>
    {:else}
        <div id="searchResults" class="mt-3">
            {#each $normalizedResults as course (course.school + course.subject + course.number + course.name)}
                <article class="course">
                    {#if course.school && ($searchStore.school || "").toUpperCase() === "ALL"}
                        <div class="course-header">
                            <span
                                class="school-chip"
                                style={`background-color: ${course.schoolColor};`}
                            >
                                {course.school}
                            </span>
                            <p class="course-title">
                                <strong>{course.subject} {course.number}: {course.name}</strong>
                            </p>
                        </div>
                    {:else}
                        <p class="course-title">
                            <strong>{course.subject} {course.number}: {course.name}</strong>
                        </p>
                    {/if}
                    <p>{course.description}</p>
                    <div class="course-meta">
                        {#if course.creditHours}
                            <span class="meta">{course.creditHours} credit hour(s)</span>
                        {/if}
                        {#if typeof course.similarity === "number"}
                            <span class="meta meta-muted">
                                similarity {course.similarity.toFixed(3)}
                            </span>
                        {/if}
                    </div>
                </article>
            {/each}
        </div>
    {/if}
</main>
