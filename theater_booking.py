import threading
import queue
import random
import time


class TheaterSystem:
    def __init__(self):
        self.global_available_seats = 300
        self.global_booked_seats = 0
        self.global_cancelled_seats = 0
        self.audit_log = []
        self.lock = threading.Lock()

    def read_global_seats(self):
        return self.global_available_seats  # intentional stale read, no lock

    def sync_memory(self, counter_id, round_id, local_queue):
        with self.lock:
            requested_bookings = 0
            requested_cancellations = 0

            while not local_queue.empty():
                op, seats = local_queue.get()
                if op == "book":
                    requested_bookings += seats
                else:
                    requested_cancellations += seats

            available = self.global_available_seats + requested_cancellations
            if requested_bookings > available:
                rejected = requested_bookings - available
                applied_bookings = available
            else:
                rejected = 0
                applied_bookings = requested_bookings

            self.global_booked_seats += applied_bookings
            self.global_cancelled_seats += requested_cancellations
            self.global_available_seats = self.global_available_seats - applied_bookings + requested_cancellations

            self.audit_log.append({
                "counter_id": counter_id,
                "round_id": round_id,
                "applied_bookings": applied_bookings,
                "applied_cancellations": requested_cancellations,
                "rejected": rejected,
                "seats_after": self.global_available_seats,
            })

            print(f"[SYNC - S] Counter {counter_id} syncing Round {round_id}...")
            print(f"[SYNC - S] Applied bookings: {applied_bookings}")
            print(f"[SYNC - S] Applied cancellations: {requested_cancellations}")
            print(f"[SYNC - S] Rejected bookings (overbook protection): {rejected}")
            print(f"[SYNC - S] Global seats after sync: {self.global_available_seats}")


class Counter:
    def __init__(self, counter_id, system):
        self.counter_id = counter_id
        self.system = system

    def run_round(self, round_id):
        print(f"Counter {self.counter_id} preparing Round {round_id} local operations...")

        stale = self.system.read_global_seats()
        print(f"-> Counter {self.counter_id}, Round {round_id}, reads global seats: {stale} (may be stale)")

        local_queue = queue.Queue()
        total_book_seats = 0
        total_cancel_seats = 0
        for _ in range(random.randint(3, 8)):
            seats = random.randint(8, 25)
            total_book_seats += seats
            local_queue.put(("book", seats))
        for _ in range(random.randint(1, 4)):
            seats = random.randint(1, 6)
            total_cancel_seats += seats
            local_queue.put(("cancel", seats))

        print(f"Counter {self.counter_id} plans: {total_book_seats} booking-seats, {total_cancel_seats} cancellation-seats (based on stale view of {stale})")

        time.sleep(random.uniform(0.05, 0.15))

        self.system.sync_memory(self.counter_id, round_id, local_queue)


if __name__ == "__main__":
    system = TheaterSystem()
    counters = [Counter(i + 1, system) for i in range(4)]

    for round_id in range(1, 6):
        print(f"\n========== ROUND {round_id} ==========")
        threads = [threading.Thread(target=c.run_round, args=(round_id,)) for c in counters]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    expected = 300 - system.global_booked_seats + system.global_cancelled_seats
    invariant = "PASS" if expected == system.global_available_seats else "FAIL"

    print("================ FINAL REPORT ================")
    print(f"Initial seats: 300")
    print(f"Total booked seats (applied): {system.global_booked_seats}")
    print(f"Total cancelled seats (applied): {system.global_cancelled_seats}")
    print(f"Final global available seats: {system.global_available_seats}")
    print(f"Expected available seats from invariant: {expected}")
    print(f"Invariant check: {invariant}")
    print("==============================================")
