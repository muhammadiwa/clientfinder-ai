/**
 * useOptimisticMessages — F4 optimistic UI for Outreach mutations.
 *
 * T8.5+++++++ Group 2: TanStack Query F4 optimistic UI.
 *
 * Pattern:
 *   1. User clicks "Approve" on a message
 *   2. We IMMEDIATELY update the local messages state
 *      (e.g. remove from pending_approval tab since the
 *      status is now 'approved')
 *   3. We await the API call
 *   4. On success: the local state is already correct;
 *      we just reload() to sync with the server
 *   5. On failure: we RESTORE the original messages
 *      (rollback) and show the error toast
 *
 * Why this matters: the R10 review queue is the most
 * time-sensitive surface. When you approve 20 messages,
 * you want them to disappear from the pending tab
 * IMMEDIATELY, not after a 5-second wait while the
 * server processes 20 sequential API calls.
 */
import { useCallback, useState } from "react";

import type { Message } from "@/types";

/**
 * Optimistically update the messages state to remove
 * the given ids (since their status changed and they're
 * no longer in the current tab).
 *
 * Returns a function that, when called, restores the
 * original state — use it in the catch block.
 */
export function useOptimisticMessages(
  currentMessages: Message[],
  setMessages: (next: Message[]) => void,
) {
  // Track the pre-optimistic state so we can rollback
  const [snapshot, setSnapshot] = useState<Message[] | null>(null);

  /**
   * Optimistically remove messages with the given ids.
   * The id set is captured as a Set for O(1) lookup.
   */
  const optimisticallyRemove = useCallback(
    (ids: Iterable<string>) => {
      const idSet = new Set(ids);
      if (idSet.size === 0) return;
      setSnapshot(currentMessages);
      setMessages(currentMessages.filter((m) => !idSet.has(m.id)));
    },
    [currentMessages, setMessages],
  );

  /**
   * Rollback to the pre-optimistic state.
   * Call this in the catch block.
   */
  const rollback = useCallback(() => {
    if (snapshot) {
      setMessages(snapshot);
      setSnapshot(null);
    }
  }, [snapshot, setMessages]);

  /**
   * Clear the snapshot (call on success to free memory).
   */
  const clearSnapshot = useCallback(() => {
    setSnapshot(null);
  }, []);

  return { optimisticallyRemove, rollback, clearSnapshot };
}

/**
 * Higher-level helper: apply an optimistic mutation
 * to the messages list with automatic rollback on error.
 *
 * Usage:
 *   const applyOptimistic = useApplyOptimistic(messages, setMessages);
 *
 *   const handleApprove = async (id: string) => {
 *     await applyOptimistic([id], async () => {
 *       await approveMessage(id, { approve: true });
 *     }, t.outreach.approvedToast, t.outreach.approvalFailed);
 *   };
 */
export function useApplyOptimistic(
  currentMessages: Message[],
  setMessages: (next: Message[]) => void,
) {
  return useCallback(
    async (
      ids: string[],
      mutation: () => Promise<void>,
    ) => {
      // Snapshot for rollback
      const snapshot = currentMessages;
      const idSet = new Set(ids);
      if (idSet.size > 0) {
        setMessages(currentMessages.filter((m) => !idSet.has(m.id)));
      }
      try {
        await mutation();
      } catch {
        // Rollback on any error
        setMessages(snapshot);
        throw new Error("mutation failed");
      }
    },
    [currentMessages, setMessages],
  );
}
