/**
 * Helix Browser Client
 * ====================
 * Main thread client that connects to NATS via WebSocket,
 * subscribes to task queue, and dispatches to WASM worker.
 */

class HelixBrowserClient {
    constructor(options = {}) {
        this.natsUrl = options.natsUrl || 'ws://localhost:8080';  // NATS WebSocket
        this.workerId = options.workerId || this.generateWorkerId();
        this.wasmBaseUrl = options.wasmBaseUrl || '/wasm/';

        this.nc = null;  // NATS connection
        this.worker = null;  // WASM Web Worker
        this.isConnected = false;
        this.taskQueue = [];
        this.pendingTasks = new Map();

        // Event handlers
        this.onConnect = options.onConnect || (() => { });
        this.onDisconnect = options.onDisconnect || (() => { });
        this.onTask = options.onTask || (() => { });
        this.onResult = options.onResult || (() => { });
        this.onError = options.onError || (() => { });
    }

    /**
     * Generate a unique worker ID
     */
    generateWorkerId() {
        return 'browser-' + Math.random().toString(36).substring(2, 10);
    }

    /**
     * Initialize the WASM worker
     */
    initWorker() {
        if (this.worker) {
            return;
        }

        this.worker = new Worker('helix-worker.js');

        this.worker.onmessage = (event) => {
            const { type, taskId, ...data } = event.data;

            switch (type) {
                case 'result':
                    this.handleWorkerResult(taskId, data);
                    break;
                case 'pong':
                    console.log('[Client] Worker pong received');
                    break;
                case 'error':
                    console.error('[Client] Worker error:', data.error);
                    this.onError(data.error);
                    break;
            }
        };

        this.worker.onerror = (error) => {
            console.error('[Client] Worker error:', error);
            this.onError(error.message);
        };

        console.log('[Client] WASM Worker initialized');
    }

    /**
     * Connect to NATS server
     */
    async connect() {
        console.log(`[Client] Connecting to NATS at ${this.natsUrl}...`);

        try {
            // Initialize worker first
            this.initWorker();

            // Connect to NATS via WebSocket
            // Using nats.ws library (must be loaded via script tag)
            if (typeof nats === 'undefined') {
                throw new Error('NATS library not loaded. Include nats.ws script.');
            }

            this.nc = await nats.connect({
                servers: this.natsUrl,
                name: this.workerId
            });

            this.isConnected = true;
            console.log(`[Client] Connected as ${this.workerId}`);

            // Subscribe to task queue (as queue group for load balancing)
            await this.subscribeToTasks();

            // Subscribe to ping requests
            await this.subscribeToPing();

            this.onConnect({ workerId: this.workerId });

        } catch (error) {
            console.error('[Client] Connection failed:', error);
            this.onError(`Connection failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * Subscribe to WASM task queue
     */
    async subscribeToTasks() {
        const subject = 'helix.tasks.wasm';
        const queueGroup = 'wasm-workers';

        const sub = this.nc.subscribe(subject, { queue: queueGroup });
        console.log(`[Client] Subscribed to ${subject} (queue: ${queueGroup})`);

        // Process incoming tasks
        (async () => {
            for await (const msg of sub) {
                try {
                    const task = JSON.parse(new TextDecoder().decode(msg.data));
                    await this.handleTask(task, msg);
                } catch (error) {
                    console.error('[Client] Error processing task:', error);
                    if (msg.reply) {
                        const errorResponse = JSON.stringify({
                            error: error.message,
                            worker_id: this.workerId
                        });
                        msg.respond(new TextEncoder().encode(errorResponse));
                    }
                }
            }
        })();
    }

    /**
     * Subscribe to ping requests
     */
    async subscribeToPing() {
        const subject = 'helix.tasks.wasm.ping';
        const sub = this.nc.subscribe(subject);

        (async () => {
            for await (const msg of sub) {
                const response = JSON.stringify({
                    worker_id: this.workerId,
                    workers: 1,
                    timestamp: Date.now()
                });
                msg.respond(new TextEncoder().encode(response));
            }
        })();
    }

    /**
     * Handle incoming task
     */
    async handleTask(task, msg) {
        const { task_id, wasm_path, input } = task;

        console.log(`[Client] Received task ${task_id}: ${wasm_path}`);
        this.onTask(task);

        // Resolve WASM path
        const fullWasmPath = wasm_path.startsWith('http')
            ? wasm_path
            : this.wasmBaseUrl + wasm_path;

        // Store the message for reply
        this.pendingTasks.set(task_id, msg);

        // Dispatch to worker
        this.worker.postMessage({
            type: 'execute',
            taskId: task_id,
            wasmPath: fullWasmPath,
            input: input
        });
    }

    /**
     * Handle result from worker
     */
    handleWorkerResult(taskId, result) {
        console.log(`[Client] Task ${taskId} completed:`, result.success);

        const msg = this.pendingTasks.get(taskId);
        this.pendingTasks.delete(taskId);

        // Build response
        const response = {
            task_id: taskId,
            worker_id: this.workerId,
            success: result.success,
            output: result.output,
            error: result.error,
            execution_time_ms: result.executionTimeMs
        };

        this.onResult(response);

        // Reply to NATS request
        if (msg && msg.reply) {
            msg.respond(new TextEncoder().encode(JSON.stringify(response)));
        }
    }

    /**
     * Disconnect from NATS
     */
    async disconnect() {
        if (this.nc) {
            await this.nc.close();
            this.nc = null;
        }

        if (this.worker) {
            this.worker.terminate();
            this.worker = null;
        }

        this.isConnected = false;
        console.log('[Client] Disconnected');
        this.onDisconnect();
    }

    /**
     * Get connection status
     */
    getStatus() {
        return {
            connected: this.isConnected,
            workerId: this.workerId,
            pendingTasks: this.pendingTasks.size
        };
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { HelixBrowserClient };
}
