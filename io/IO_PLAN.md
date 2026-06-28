# IO System Vision Document

Copyright © 2026 Justin K. Lietz, Neuroca, Inc. All Rights Reserved.
Dual-licensed for open academic research and commercial deployment.

---

## 1. Core Paradigm

The Void Dynamics Model (VDM) treats all machine actions: mechanical movement, sound modulation, text generation, and code execution: as unified motor outputs.
The system rejects hardcoded semantic representations or engineered mappings (e.g., direct string-to-string or text-to-speech generation). Instead, it provides a fixed, unyielding structural boundary of unchanging neuron groups (lanes/indices).
The model starts with no innate understanding of its body or language. It must discover the topology of its inputs and outputs through the statistical correlations and temporal feedback of its own continuous sensorimotor loop.

---

## 2. System Topology

The architecture is divided into two decoupled environments: hardware-aware translation/execution (io/) and the abstract, mathematical core (core/sensorimotor/).

                    [ CORE / SENSORIMOTOR / ]
              (Agnostic Math & Neural Dynamics)
                     /                        \
       (Efferent Spikes)                     (Afferent Indices)
                   /                            \
           [ efference/ ]                  [ afference/ ]
                  │                               ▲
                  │                       [ sensorimotor_aperture ]
                  ▼                               │
---
                     [ IO / TRANSDUCTION / ]
                     (The Translation Matrix)
                  │                               ▲
        [ efference_*.py ]                 [ afference.py ]
                  │                               ▲
                  ▼                               │
              [ utd.py ] ───► [ os_router.py ] ───► [ ute.py ]
         (Outbound Gate)                     (Inbound Receptor)
                  │                               ▲
                  ▼                               │
        [ EXECUTOR ENDPOINTS ] ────────────► [ SENSORY ECHOES ]
     (Motors / Audio / Keyboard / OS)        (Proprioception / Feedback)

---

## 3. Directory Blueprint

### 3.1 Input/Output Layer (io/)

Mantains low-level hardware interfaces, OS subsystem links, and asynchronous telemetry logging.

* io/utd.py (Universal Transduction Device): The final outbound gate. It commits actuation payloads to logs under trace_kind="utd_actuation" before driving the handlers.
* io/ute.py (Universal Temporal Encoder): The inbound queue-style receptor boundary. It captures input events and writes them directly to compressed files (motor_traces.jsonl.zst).
* io/os_router.py: A data traffic controller. It reads the action type emitted by the UTD and dispatches it to the correct low-level endpoint driver.
* io/transduction/: The translation matrix. It houses the code that maps abstract core neural indices to concrete physical or virtual channel lanes.
* efference_motor.py / efference_keyboard.py / efference_vocal.py / efference_os.py
   * afference.py / reafference.py
* io/actuators/: Raw communication bus drivers (CAN bus, SPI, PWM) for joint control.
* io/audio/: Converts vocal channel traces directly into synthetic sound waves via system audio layers.
* io/virtual_keyboard/: Simulates physical keyboard actuation via the Linux kernel's /dev/uinput subsystem.
* io/OS_interface/: Manages an unprivileged Docker runtime container (sandbox_runtime.py) to execute shell commands or code written by the model's virtual typing.

### 3.2 Core Sensorimotor Module (core/sensorimotor/)

A hardware-agnostic matrix driven purely by the timing and spatial distribution of neural spikes.

* efference/: Manages outbound motor intentions.
* basis.py / trace.py: Space layout and historical log of output neuron groups.
   * observer.py: Passive diagnostic tracker that logs motor profiles without altering behavior.
* reafference/: Explicit software tracking layer for closed-loop analysis.
* loop_basis.py / loop_trace.py / observation.py: Measures time delays, cross-correlations, and internal state echoes caused by self-generated movement.
* afference/: Processes incoming input arrays.
* basis.py / trace.py: Unyielding entry points and logs for incoming neural indices.
   * sensorimotor_aperture.py: Non-semantic attention gate (thalamic gating). It attenuates or occludes input volume to shield the core from noise based on total network activity.
   * preprocessing/: Handles biological-grade contrast sharpening (lateral_inhibition.py) and scaling normalization (sensory_adaptation.py).

---

## 4. Unmapped Actuation Interfaces

### 4.1 Keyboard Coordinate Grid

Characters are not mapped to specific neurons. io/virtual_keyboard/key_matrix.py exposes a raw, unmapped 2D spatial layout.
The core sends continuous signals down fixed Row and Column lanes. The transduction layer calculates the center of mass across these lanes to derive a raw [Row, Column] grid intersection. The model must discover through experience which coordinate combinations generate meaningful text feedback on its sensory input.

### 4.2 Sandboxed Code Execution

When the model types valid syntax and fires a dedicated system-execution lane, io/OS_interface/sandbox_runtime.py runs the payload inside an isolated container. The resulting stdout and error streams are converted back into afferent sensory pulses, letting the model experience the computational results of its actions.

---

## 5. Data Storage & Tracking

The framework generates dense timeline files across diverse experiment regimes:

VDM-Research-Data/  
├── README.md                      # Contains viewer: false to disable table parser  
├── scripts/                       # Telemetry utility and data tools  
├── experiments/                   # Actuation, Afference, and Occlusion traces  
├── legacy-runs/                   # Historical snapshot geometry logs  
└── v0.8.2-alpha_runs/             # Time-normalization smoke test datasets  

To avoid overloading lightweight code repositories, all experimental directories, compressed logs (.jsonl.zst), and analytical notebooks will be kept entirely on an external storage drive path and on a Hugging Face dataset repository: jlietz93/VDM-Research-Data

These files are backed up to the cloud via the hf dataset engine. Because the database contains deeply nested directories instead of flat tables, the root README.md uses an explicit override configuration (viewer: false). This bypasses the default flat database parser and tells the cloud platform to display the asset directories as a standard, navigable file-tree.
