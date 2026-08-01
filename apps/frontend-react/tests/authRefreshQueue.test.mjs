import test from 'node:test'
import assert from 'node:assert/strict'
import { createAuthRefreshQueue } from '../src/lib/authRefreshQueue.js'

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

test('concurrent 401s share one refresh and all get the new token', async () => {
  let refreshCalls = 0
  const gate = deferred()
  const queue = createAuthRefreshQueue({
    refreshAccessToken: async () => {
      refreshCalls += 1
      return gate.promise
    },
  })

  const first = queue.runSingleFlight()
  // Let the first caller enter refreshing=true before enqueueing waiters.
  await Promise.resolve()
  assert.equal(queue.isRefreshing, true)

  const second = queue.runSingleFlight()
  const third = queue.runSingleFlight()
  assert.equal(queue.waiterCount, 2)

  gate.resolve('access-token-v2')
  const tokens = await Promise.all([first, second, third])
  assert.deepEqual(tokens, ['access-token-v2', 'access-token-v2', 'access-token-v2'])
  assert.equal(refreshCalls, 1)
  assert.equal(queue.isRefreshing, false)
  assert.equal(queue.waiterCount, 0)
})

test('refresh failure rejects every waiter and invokes onRefreshFailed once', async () => {
  let failed = 0
  const gate = deferred()
  const queue = createAuthRefreshQueue({
    refreshAccessToken: async () => gate.promise,
    onRefreshFailed: () => {
      failed += 1
    },
  })

  const first = queue.runSingleFlight()
  await Promise.resolve()
  const second = queue.runSingleFlight()

  gate.reject(new Error('refresh_dead'))
  await assert.rejects(first, /refresh_dead/)
  await assert.rejects(second, /refresh_dead/)
  assert.equal(failed, 1)
  assert.equal(queue.isRefreshing, false)
})

test('sequential refresh after success starts a new single-flight', async () => {
  let refreshCalls = 0
  const queue = createAuthRefreshQueue({
    refreshAccessToken: async () => {
      refreshCalls += 1
      return `token-${refreshCalls}`
    },
  })

  assert.equal(await queue.runSingleFlight(), 'token-1')
  assert.equal(await queue.runSingleFlight(), 'token-2')
  assert.equal(refreshCalls, 2)
})
