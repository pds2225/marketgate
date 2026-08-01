/**
 * Single-flight token refresh with waiter queue.
 *
 * Without a queue, a second 401 while refresh is in flight is rejected
 * immediately (see docs/LESSONS.md L023). On /payment/callback that drops
 * POST /v1/payment/confirm while balance sync holds the refresh lock.
 */

export function createAuthRefreshQueue({ refreshAccessToken, onRefreshFailed }) {
  let refreshing = false
  let waiters = []

  function flushWaiters(error, token) {
    const pending = waiters
    waiters = []
    for (const waiter of pending) {
      if (error) waiter.reject(error)
      else waiter.resolve(token)
    }
  }

  async function runSingleFlight() {
    if (refreshing) {
      return new Promise((resolve, reject) => {
        waiters.push({ resolve, reject })
      })
    }

    refreshing = true
    try {
      const token = await refreshAccessToken()
      flushWaiters(null, token)
      return token
    } catch (error) {
      flushWaiters(error)
      onRefreshFailed?.(error)
      throw error
    } finally {
      refreshing = false
    }
  }

  return {
    runSingleFlight,
    /** Test/inspection only */
    get isRefreshing() {
      return refreshing
    },
    get waiterCount() {
      return waiters.length
    },
  }
}
