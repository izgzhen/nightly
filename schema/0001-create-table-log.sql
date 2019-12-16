CREATE TABLE IF NOT EXISTS log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    job_name TEXT NOT NULL,
    job_steps TEXT NOT NULL, -- only the finished ones
    job_persisted TEXT, -- JSON string of persisted field in job config, null if job failed
    job_started DATETIME NOT NULL,
    job_finished DATETIME NOT NULL, -- time for either failed or success run
    job_status ENUM('ok', 'failed') NOT NULL,
    storage TEXT, -- JSON string of storage used, null if job failed
    compute TEXT NOT NULL -- JSON string of compute used
);