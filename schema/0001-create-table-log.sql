CREATE TABLE IF NOT EXISTS log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    job_name TEXT NOT NULL,
    job_steps TEXT NOT NULL, -- JSON string
    job_persisted TEXT NOT NULL,
    job_started DATETIME NOT NULL,
    job_finished DATETIME, -- time for either failed or success run
    job_status ENUM('running', 'ok', 'failed') NOT NULL,
    storage TEXT, -- JSON string of storage used, null if job failed
    compute TEXT NOT NULL, -- JSON string of compute used
    stderr TEXT,
    stdout TEXT,
    pid    INT -- runner task PID
);