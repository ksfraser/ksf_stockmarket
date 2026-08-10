<?php
/**
 * Event publisher — enqueue domain events from PHP into MariaDB event_queue.
 */

if (!function_exists('event_publisher_db_connect')) {
    function event_publisher_db_connect(): ?mysqli {
        static $conn = null;
        if ($conn !== null) {
            return $conn;
        }

        $host = 'ksfraser.ca';
        $port = 3306;
        $user = 'ksfraser_stockmarket';
        $pass = 'Zaqwsx9sm1@';
        $db   = 'ksfraser_stock_market';

        try {
            $conn = new mysqli($host, $user, $pass, $db, (int)$port);
            if ($conn->connect_error) {
                $conn = null;
                error_log('event_publisher connect error: ' . $conn->connect_error);
                return null;
            }
            $conn->set_charset('utf8mb4');
            return $conn;
        } catch (Throwable $e) {
            error_log('event_publisher connect exception: ' . $e->getMessage());
            return null;
        }
    }
}

if (!function_exists('event_publisher_enqueue')) {
    function event_publisher_enqueue(string $type, array $payload, ?string $event_id = null): bool
    {
        if ($event_id === null) {
            $event_id = uniqid('evt_', true);
        }

        $conn = event_publisher_db_connect();
        if ($conn === null) {
            return false;
        }

        $sql = "INSERT INTO event_queue (event_id, event_type, payload, status, occurred_at, attempts, last_error)
                VALUES (?, ?, ?, 'pending', NOW(), 0, NULL)";
        $stmt = $conn->prepare($sql);
        if ($stmt === false) {
            error_log('event_publisher prepare failed: ' . $conn->error);
            return false;
        }

        $json = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if ($json === false) {
            $json = '{}';
        }

        try {
            $stmt->bind_param('sss', $event_id, $type, $json);
            $ok = $stmt->execute();
            if (!$ok) {
                error_log('event_publisher execute failed: ' . $stmt->error);
                return false;
            }
            return true;
        } catch (Throwable $e) {
            error_log('event_publisher exception: ' . $e->getMessage());
            return false;
        }
    }
}
