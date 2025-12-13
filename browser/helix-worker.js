/**
 * Helix WASM Worker
 * =================
 * Web Worker that loads and executes WASM modules.
 * Communicates with main thread via postMessage.
 */

// Cache for loaded WASM modules
const wasmCache = new Map();

/**
 * Load a WASM module from URL or cached
 */
async function loadWasm(wasmPath) {
    // Check cache first
    if (wasmCache.has(wasmPath)) {
        console.log(`[Worker] Using cached WASM: ${wasmPath}`);
        return wasmCache.get(wasmPath);
    }

    console.log(`[Worker] Loading WASM: ${wasmPath}`);

    try {
        const response = await fetch(wasmPath);
        if (!response.ok) {
            throw new Error(`Failed to fetch WASM: ${response.statusText}`);
        }

        const wasmBytes = await response.arrayBuffer();

        // For WASI modules, we need to provide imports
        // Using a minimal WASI shim
        const wasiImports = createWasiShim();

        const { instance, module } = await WebAssembly.instantiate(
            wasmBytes,
            { wasi_snapshot_preview1: wasiImports }
        );

        // Cache the module (not instance, as instances hold state)
        wasmCache.set(wasmPath, module);

        return { instance, module };
    } catch (error) {
        console.error(`[Worker] Failed to load WASM: ${error}`);
        throw error;
    }
}

/**
 * Create a minimal WASI shim for WASM execution
 * Captures stdout for result extraction
 */
function createWasiShim() {
    let stdoutBuffer = [];
    let stderrBuffer = [];

    // Memory will be set when we get the instance
    let memory = null;

    return {
        // Args - we'll inject these
        args_get: (argv, argvBuf) => 0,
        args_sizes_get: (argc, argvBufSize) => {
            // Will be overwritten by execute()
            return 0;
        },

        // Environment
        environ_get: () => 0,
        environ_sizes_get: (environCount, environBufSize) => {
            if (memory) {
                new Uint32Array(memory.buffer, environCount, 1)[0] = 0;
                new Uint32Array(memory.buffer, environBufSize, 1)[0] = 0;
            }
            return 0;
        },

        // Clock
        clock_time_get: (id, precision, time) => {
            const now = BigInt(Date.now()) * BigInt(1000000);
            if (memory) {
                new BigUint64Array(memory.buffer, time, 1)[0] = now;
            }
            return 0;
        },

        // File descriptors (minimal impl)
        fd_write: (fd, iovs, iovsLen, nwritten) => {
            if (!memory) return 0;

            const view = new DataView(memory.buffer);
            let written = 0;

            for (let i = 0; i < iovsLen; i++) {
                const ptr = view.getUint32(iovs + i * 8, true);
                const len = view.getUint32(iovs + i * 8 + 4, true);

                const bytes = new Uint8Array(memory.buffer, ptr, len);
                const text = new TextDecoder().decode(bytes);

                if (fd === 1) { // stdout
                    stdoutBuffer.push(text);
                } else if (fd === 2) { // stderr
                    stderrBuffer.push(text);
                }

                written += len;
            }

            view.setUint32(nwritten, written, true);
            return 0;
        },

        fd_close: () => 0,
        fd_seek: () => 0,
        fd_read: () => 0,
        fd_fdstat_get: () => 0,
        fd_prestat_get: () => 8, // EBADF - no preopened dirs
        fd_prestat_dir_name: () => 8,

        // Process
        proc_exit: (code) => {
            throw new WasiExit(code);
        },

        // Random
        random_get: (buf, bufLen) => {
            if (memory) {
                const bytes = new Uint8Array(memory.buffer, buf, bufLen);
                crypto.getRandomValues(bytes);
            }
            return 0;
        },

        // Get captured output
        getStdout: () => stdoutBuffer.join(''),
        getStderr: () => stderrBuffer.join(''),
        clearBuffers: () => {
            stdoutBuffer = [];
            stderrBuffer = [];
        },
        setMemory: (mem) => { memory = mem; }
    };
}

/**
 * Custom error for WASI proc_exit
 */
class WasiExit extends Error {
    constructor(code) {
        super(`WASI exit with code ${code}`);
        this.code = code;
    }
}

/**
 * Execute a WASM module with input
 */
async function executeWasm(wasmPath, input) {
    const startTime = performance.now();

    try {
        // Create fresh WASI shim for this execution
        const wasiShim = createWasiShim();

        // Load the module
        const response = await fetch(wasmPath);
        const wasmBytes = await response.arrayBuffer();

        // Prepare args (program name + input)
        const args = ['agent', input];

        // Create imports with args
        const imports = {
            wasi_snapshot_preview1: {
                ...wasiShim,
                args_sizes_get: (argcPtr, argvBufSizePtr) => {
                    // Will be filled after we have memory
                    return 0;
                },
                args_get: (argvPtr, argvBufPtr) => {
                    return 0;
                }
            }
        };

        const { instance } = await WebAssembly.instantiate(wasmBytes, imports);

        // Set memory reference in shim
        if (instance.exports.memory) {
            wasiShim.setMemory(instance.exports.memory);
        }

        // Call _start (WASI entry point)
        let exitCode = 0;
        try {
            if (instance.exports._start) {
                instance.exports._start();
            } else if (instance.exports.main) {
                instance.exports.main();
            }
        } catch (e) {
            if (e instanceof WasiExit) {
                exitCode = e.code;
            } else {
                throw e;
            }
        }

        const stdout = wasiShim.getStdout();
        const stderr = wasiShim.getStderr();

        const executionTime = performance.now() - startTime;

        // Try to parse stdout as JSON
        let output;
        try {
            output = JSON.parse(stdout);
        } catch {
            output = stdout;
        }

        return {
            success: exitCode === 0,
            output: output,
            stderr: stderr,
            exitCode: exitCode,
            executionTimeMs: executionTime
        };

    } catch (error) {
        return {
            success: false,
            error: error.message,
            executionTimeMs: performance.now() - startTime
        };
    }
}

/**
 * Handle messages from main thread
 */
self.onmessage = async function (event) {
    const { type, taskId, wasmPath, input } = event.data;

    switch (type) {
        case 'execute':
            console.log(`[Worker] Executing task ${taskId}`);
            const result = await executeWasm(wasmPath, input);
            self.postMessage({
                type: 'result',
                taskId: taskId,
                ...result
            });
            break;

        case 'ping':
            self.postMessage({ type: 'pong', timestamp: Date.now() });
            break;

        case 'clear-cache':
            wasmCache.clear();
            self.postMessage({ type: 'cache-cleared' });
            break;

        default:
            console.warn(`[Worker] Unknown message type: ${type}`);
    }
};

console.log('[Helix Worker] Initialized and ready');
