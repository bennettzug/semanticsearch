import { writable } from "svelte/store";

const initialState = {
    query: "",
    school: null,
    results: [],
    status: "idle",
    error: null,
};

function createSearchStore() {
    const { subscribe, set, update } = writable(initialState);

    return {
        subscribe,
        reset() {
            set(initialState);
        },
        start(query, school) {
            update(() => ({ query, school, results: [], status: "loading", error: null }));
        },
        succeed(query, school, results) {
            set({ query, school, results, status: "success", error: null });
        },
        fail(query, school, error) {
            set({ query, school, results: [], status: "error", error });
        },
    };
}

export const searchStore = createSearchStore();
