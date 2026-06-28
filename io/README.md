# VDM Runtime I/O Module (io/)
This directory acts as the Hardware/OS Boundary for the VDM Runtime framework. Its primary responsibility is managing the transition between the real physical/virtual world and the abstract, agnostic neural core.
It isolates all low-level hardware protocols, operating system hooks, asynchronous queues, and raw data formatters, ensuring that core/sensorimotor/ remains entirely unbiased and independent of the physical body layout.
------------------------------
## 📂 Directory Structure

io/
├── README.md                      # This file
├── utd.py                         # Universal Transduction Device (Final outbound execution gate)
├── ute.py                         # Universal Temporal Encoder (Initial inbound receptor queue)
├── os_router.py                   # 2. <--- CATCHES PACKET FROM UTD ➔ routes to the right driver if needed

│
├── transduction/                  # THE TRANSLATION MATRIX (Core Neurons ⇄ Channels)
│   ├── afference.py               # Raw UTE receptor inputs ➔ Fixed input neural indices
│   ├── reafference.py             # Intercepts self-generated physical execution echoes
│   │
│   ├── efference_motor.py         # Outbound neural spikes ➔ CAN bus joint channel coordinates
│   ├── efference_vocal.py         # Outbound neural spikes ➔ Phoneme/Formant wave frequencies
│   ├── efference_keyboard.py      # Outbound neural spikes ➔ Row/Column grid key coordinate packets
│   └── efference_os.py            # Outbound neural spikes ➔ Isolated shell/container execution hooks
│
├── actuators/                     # PHYSICAL MOTOR LINKS
│   └── motor_can_bus.py           # Native bus drivers, joint limits, and hardware links
│
├── audio/                         # SOUND MODULATION LYSERS
│   ├── phoneme_generator.py       # Converts vocal trace streams into raw synthetic sound waves
│   └── sound_driver.py            # Direct interface to OS sound servers (PipeWire / ALSA)
│
├── virtual_keyboard/              # CHARACTER INTERFACE
│   ├── key_matrix.py              # X/Y grid mapping for raw structural character coordination
│   └── uinput_link.py             # Linux kernel virtual HID injector (/dev/uinput)
│
└── OS_interface/                  # COMPUTATIONAL EXECUTION ENDPOINTS
    ├── sandbox_runtime.py         # Secure Docker / Container execution jail for typed code
    └── syscall_driver.py          # Translates system channel triggers into low-level bash calls

------------------------------
## ⚙️ Core Architectural Components

### 1. Boundary Interfaces (utd.py & ute.py)
These two files serve as the rigid structural boundaries where software abstraction meets real-world execution.

* ute.py (Universal Temporal Encoder): A thread-safe, queue-style receptor boundary. It strips out legacy streaming protocols and processes raw hardware/virtual input events through push(). It serializes these timeline events directly into compressed high-fidelity storage (motor_traces.jsonl.zst) before passing them forward.
* utd.py (Universal Transduction Device): The virtual Neuromuscular Junction. It receives explicit actuation payloads, commits them to the chronological trace log under trace_kind="utd_actuation", and commands the downstream physical or virtual endpoints. It has no knowledge of language or macros; it handles raw event emission only.

### 2. Transduction Layer (io/transduction/)
The translation matrix of the framework. It ensures that the model does not require an engineered "body schema." Instead, it flattens real-world systems into raw coordinate spaces, allowing the core's internal self-organizing dynamics (e.g., STDP) to learn the topology of the system organically.

* Afferent Transduction: Takes incoming events from ute.py and resolves them into a raw, fixed array of unchangeable input neural indices.
* Efferent Transduction: Takes abstract spikes from the motor core and maps them onto specific physical/virtual channels (Motors, Vocal Tract, Keyboard Coordinates, System Hooks).

### 3. Execution Endpoints (Hardware, Sound, Keyboard, OS)
The "muscles" and "vocal cords" driven by the UTD.

* actuators/: Translates motor coordinate channels into raw digital bus packets (like CAN, SPI, or PWM) to create real mechanical torque.
* audio/: Receives continuous vocal trace channels and modulates them directly into raw speaker waveforms.
* virtual_keyboard/: Treats character generation like a physical muscle task. The model coordinates raw traces to fire intersecting points on a 2D [Row, Column] matrix, which are injected into the OS as true keystrokes via /dev/uinput.
* OS_interface/: Takes text written by the virtual keyboard and executes it inside an isolated sandbox environment. Output and terminal results are fed straight back into the UTE queue as sensory afference.

------------------------------

### 🔄 Data Lifecycle Example (The Sensorimotor Loop)

 [ core/efference/ ]                 # 1. Agnostic Motor Neurons Spike
         │
         ▼
 [ io/transduction/efference_* ]     # 2. Transduction maps Spikes to Coordinates
         │
         ▼
 [ io/utd.py ]                       # 3. UTD logs the intention to motor_traces
         │
         ▼
 [ io/virtual_keyboard/ ]            # 4. Driver injects physical OS event
         │
         ▼ (Physical Actuation Echoes Back)
 [ io/ute.py ]                       # 5. UTE enqueues raw keystroke echo/response
         │
         ▼
 [ io/transduction/afference.py ]    # 6. Maps raw echo back to fixed Sensory Indices
         │
         ▼
 [ core/afference/ ]                 # 7. Core experiences its own output emergently

------------------------------

### 🔒 Security & Safety Principles

   1. Strict Isolation: No logic inside io/ may alter the internal mathematical states or weights of the neural core. It is an information pipe and observer layer only.
   2. Sandboxed Actuation: Code execution triggered via the OS_interface/ must be strictly contained inside an unprivileged virtual cage (sandbox_runtime.py) to safeguard the host system while the model experiments with code generation.
   3. Intellectual Property Note: This research and runtime framework are protected under a dual-license configuration to foster open academic research while aligning commercial scale applications with explicit ethical guidelines. See the global project LICENSE file for details.
