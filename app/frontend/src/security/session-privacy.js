/** Remove account-bound client state when identity is lost or changes. */
export function clearPrivateClientState(queryClient, storage) {
  queryClient.clear();
  try {
    const target = storage ?? globalThis.localStorage;
    target?.removeItem('autocare.reception.draft');
    target?.setItem('autocare.session.reset', `${Date.now()}:${Math.random()}`);
  } catch {
    // A browser that blocks storage must still be able to log out safely.
  }
}
