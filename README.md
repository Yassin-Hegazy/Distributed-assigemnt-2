# Theater Booking System — Distributed Systems Simulation

A single-file Python simulation of a **distributed theater booking system** that demonstrates **weak consistency**, **race conditions**, and **overbook protection** using threads.

---

## What It Simulates

Imagine a theater with 300 seats. There are **4 booking counters** (like ticket booths), each running independently and simultaneously. Each counter reads the current seat count, prepares a batch of bookings and cancellations locally, then syncs with the central system.

The key distributed systems concept here is **weak consistency**: a counter reads the seat count *without a lock*, so it may be working with stale (outdated) information by the time it tries to sync. This is intentional — it mirrors real-world systems where reading from a replica or cache is faster but not guaranteed to be current.

---

## Architecture

### `TheaterSystem` — the shared global state

Think of this as the central server. It holds the single source of truth.

| Attribute | Description |
|---|---|
| `global_available_seats` | Seats currently available (starts at 300) |
| `global_booked_seats` | Running total of all applied bookings |
| `global_cancelled_seats` | Running total of all applied cancellations |
| `audit_log` | List of every sync operation with full details |
| `lock` | A mutex — only one counter can sync at a time |

**`read_global_seats()`** — returns the seat count *without acquiring the lock*. This is the deliberate stale read. Multiple counters can call this simultaneously and all get what appears to be the same "truth", even though another counter may be mid-sync.

**`sync_memory(counter_id, round_id, local_queue)`** — the critical section. Acquires the lock, drains the counter's queue, applies overbook protection, updates all global counters, and logs the result.

---

### `Counter` — a worker node (booking booth)

Each counter runs independently in its own thread.

**`run_round(round_id)`** does four things in order:

1. **Reads** the global seat count without a lock (stale read)
2. **Builds** a local queue of random operations:
   - 3–8 booking operations, each for 8–25 seats
   - 1–4 cancellation operations, each for 1–6 seats
3. **Prints its intent** — what it plans to do, based on the stale number it saw
4. **Sleeps** briefly (50–150 ms) to simulate real processing time, then **syncs** with the central system

---

## How Weak Consistency Shows Up

All 4 counters read the seat count at roughly the same time — before any of them have synced. So they all see the *same stale number* and all plan bookings as if that number were still valid.

By the time they sync one by one (the lock ensures no two sync simultaneously), the real available seats may be far lower than what any counter assumed. This triggers **overbook protection**:

```
Counter 2 plans: 136 booking-seats (based on stale view of 300)
...
[SYNC - S] Applied bookings: 87
[SYNC - S] Rejected bookings (overbook protection): 49
```

Counter 2 wanted 136 seats but only 87 were left when it finally got the lock — so 49 were rejected.

---

## Overbook Protection Logic

Inside `sync_memory`, before applying bookings:

```
available = current_seats + cancellations_in_this_batch
if requested_bookings > available:
    apply only what's available, reject the rest
```

Cancellations in the same batch are counted first, so a counter that cancels seats can also use those freed seats in the same sync.

---

## Execution Flow

```
5 rounds × 4 counters = 20 sync operations total

Each round:
  ├── 4 threads start simultaneously
  ├── Each thread reads seats (no lock) → stale read
  ├── Each thread builds its local queue independently
  ├── Each thread sleeps briefly (simulates processing delay)
  └── Each thread calls sync_memory → acquires lock → one at a time
```

Rounds are sequential (all 4 threads in round N finish before round N+1 starts), but within a round all counters run in parallel.

---

## Invariant Check

At the end, the final report verifies the system's integrity with a simple accounting identity:

```
initial_seats - total_booked + total_cancelled == final_available
300 - booked + cancelled == available
```

If this holds → `PASS`. It must always pass because `sync_memory` is the only place global state changes, and it runs under a lock.

---

## Running It

```bash
python theater_booking.py
```

No dependencies beyond the Python standard library (`threading`, `queue`, `random`, `time`).

---

## Sample Output Structure

```
========== ROUND 1 ==========
Counter 1 preparing Round 1 local operations...
-> Counter 1, Round 1, reads global seats: 300 (may be stale)
Counter 1 plans: 63 booking-seats, 13 cancellation-seats (based on stale view of 300)
...
[SYNC - S] Counter 1 syncing Round 1...
[SYNC - S] Applied bookings: 63
[SYNC - S] Applied cancellations: 13
[SYNC - S] Rejected bookings (overbook protection): 0
[SYNC - S] Global seats after sync: 237

================ FINAL REPORT ================
Initial seats: 300
Total booked seats (applied): 488
Total cancelled seats (applied): 188
Final global available seats: 0
Expected available seats from invariant: 0
Invariant check: PASS
==============================================
```

---

## Key Concepts Demonstrated

| Concept | Where It Appears |
|---|---|
| Weak consistency | `read_global_seats()` — no lock, may return stale data |
| Race condition | All counters plan based on the same stale seat count |
| Mutual exclusion | `threading.Lock` in `sync_memory` ensures safe writes |
| Overbook protection | Rejected bookings when real available < requested |
| Audit log | Every sync recorded with full before/after details |
| Invariant verification | Final report checks accounting identity holds |
