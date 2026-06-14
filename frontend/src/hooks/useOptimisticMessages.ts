/**
 * useOptimisticMessages — F4 optimistic UI for Outreach mutations.
 *
 * T8.5+++++++ Group 2 (initial): local state mutations only.
 * T8.5+++++++ (cache-level): also updates the TanStack Query
 * cache via setQueryData, so other components viewing the
 * same queryKey see the update.
 *
 * Pattern (local + cache):
 *   1. User clicks "Approve" on a message
 *   2. We IMMEDIATELY:
 *      a. Snapshot the current query cache
 *      b. Remove the message from the cache (via setQueryData)
 *      c. Remove from local state (so the optimistic-UI
 *         helper still works for any UI bound to local state)
 *   3. We await the API call
 *   4. On success: cache is already correct; the next
 *      refetch will confirm
 *   5. On failure: we RESTORE both the cache and local
 *      state (rollback) and show the error toast
 *
 * Why this matters: with the previous local-only approach,
 * only THIS component saw the optimistic update. With
 * cache-level updates, ANY component bound to the same
 * queryKey (e.g. a future "pending count" badge in the
 * sidebar) sees the update immediately. Single source
 * of truth = single place to update.
 */
import { useCallback } from "react";
import { useQueryClient, type QueryKey } from "@tanstack/react-query";

import type { Message } from "@/types";

/**
 * Apply an optimistic mutation to BOTH the local messages
 * state AND the TanStack query cache, with automatic
 * rollback on error.
 *
 * Usage:
 *   const applyOptimistic = useApplyOptimistic({
 *     messages, setMessages,
 *     queryKey: messagesQueryKey,
 *   });
 *   await applyOptimistic([id], async () => {
 *     await approveMessage(id, { approve: true });
 *   });
 *
 * On success: leaves both state + cache updated.
 * On throw: rolls back BOTH, re-throws for caller to toast.
 */
export function useApplyOptimistic(opts: {
  messages: Message[];
  setMessages: (next: Message[]) => void;
  queryKey: QueryKey;
}) {
  const { messages, setMessages, queryKey } = opts;
  const queryClient = useQueryClient();

  return useCallback(
    async (
      ids: string[],
      mutation: () => Promise<void>,
    ) => {
      const idSet = new Set(ids);
      if (idSet.size === 0) {
        // No-op: just run the mutation
        try {
          await mutation();
        } catch {
          throw new Error("mutation failed");
        }
        return;
      }

      // Snapshot BOTH the local state and the cache so
      // we can roll back on error.
      const localSnapshot = messages;
      const cacheSnapshot = queryClient.getQueryData<{ items: Message[]; total: number }>(queryKey);

      // 1) Optimistic local update
      setMessages(messages.filter((m) => !idSet.has(m.id)));

      // 2) Optimistic cache update (matches the queryKey
      //    shape used by useMessages in useOutreach.ts)
      if (cacheSnapshot) {
        queryClient.setQueryData<{ items: Message[]; total: number }>(
          queryKey,
          {
            ...cacheSnapshot,
            items: cacheSnapshot.items.filter((m) => !idSet.has(m.id)),
            total: Math.max(cacheSnapshot.total - ids.length, 0),
          },
        );
      }

      try {
        await mutation();
      } catch {
        // Rollback BOTH
        setMessages(localSnapshot);
        if (cacheSnapshot !== undefined) {
          queryClient.setQueryData(queryKey, cacheSnapshot);
        }
        throw new Error("mutation failed");
      }
    },
    [messages, setMessages, queryClient, queryKey],
  );
}

/**
 * Lower-level helper for advanced use cases.
 * Returns a function that takes ids and a mutation, and
 * applies the optimistic update + rollback. Useful when
 * you need to compose with other side effects.
 */
export function useOptimisticRemove() {
  const queryClient = useQueryClient();
  return useCallback(
    (queryKey: QueryKey, ids: Iterable<string>) => {
      const idSet = new Set(ids);
      if (idSet.size === 0) return undefined;
      const snapshot = queryClient.getQueryData<{ items: Message[]; total: number }>(queryKey);
      if (snapshot) {
        queryClient.setQueryData<{ items: Message[]; total: number }>(queryKey, {
          ...snapshot,
          items: snapshot.items.filter((m) => !idSet.has(m.id)),
          total: Math.max(snapshot.total - idSet.size, 0),
        });
      }
      return snapshot; // caller can call setQueryData(queryKey, snapshot) to rollback
    },
    [queryClient],
  );
}
