# robbie
Open Source Agentic Robot.

This project will combine the different parts of robbie that have been built, as separate projects, into a whole. Some of these projects have not been made open-source, but the ones that have include:
  - 3D printable parts and assembly (https://github.com/busyDuckman/robbie_openscad)
  - Eye graphics rendering, other bits and pieces (https://github.com/busyDuckman/robbie_restoration).
  - Look around behaviour (https://github.com/busyDuckman/look_around)

The goal is to achieve a low cost agentic robot for interaction in group situations (stores, social events, meetings) and have it available under the MIT licence (the last part not easy).

New work for this repo:
  - **Robbie's personalty and agentic framework** is old (started when transformers were a novel thing) and predates modern established practices. This project will modernise that framework.

  - **Inverse-Kinematics and controller re-write.** (planned) The previous system used the camera to establish the system pose. That may sound ill-advised, but was something I wanted to try, just to push and see what was possible (it's my hobby project so I indulged my curiosity). That was abandoned, the new system puts a magnetic rotary sensor on each motor.

# Status

TRL 2, "technology concept formulated".

# Getting started.

Development is done via Linux or WSL. 
There  must be a "docker host" machine, by default the local box. You configure it in the .env as per:


There is a justfile, it . 


# Architecture  

Robbie is composed of 3 layers.

  - A) The LLM: Decides when to speak, or take an action.
  - B) The harness: State, behaviour, people present, attention target, mood, relationships. beeps, TTS. This layer is a collection of software components written in different languages. Manage mic, camera.
  - C) Robot Control: Drive motors, read sensors (encoders, home sw). ROS 2 based. Look-around, eye graphics.


This repo only covers layers A and B. Layer C is in a separate repo [TODO].

# Stand ins

This repo can run without robbie or a pi. There is a stand in for layer C and layer B can be configured to run from any machine with a microphone, webcam and speakers.

# Repo Structure

    robbie/
      .github/workflows/    CI (disabled at first)
      .plans/               planning scratch space (copy to docs when concrete)
      .models/              If a model is not found elsewhere, and we need a local copy.
      docs/                 design docs

      config/
        robbie/
          settings.schema.json
          settings.example.json
        tools/                tech stack config etc
      
      prompts/
        robbie_persona/             persona prompt files, versioned by git
        ethics/
        activity_bootstrap/

      training/

      data/                   Things that robbie can access (just fetch-data to bootstrap)
        reference_material/   Information kept by robbie, for definitive reference and RAG
          social/
            cocktail_recipes/   Social events companion
            boardgame_rules/    Games night or D&D companion.
            jokes/              Quick one liners etc
          business/
            negotiation/        Value propositions etc
            product_info/       Information about products robbie is discussing
          robbie/               Information about robbie, even some pictures of robbie for self recognition.
        images/
        audio/

      common/               Common Robbie Code that any service can use
        interfaces/
          RELM/               Robbies Expressive Language Model (what the llm outputs)
          proto/              Protobuf schemas for messages inside B (buf config here)
          ros/                (the message definitions only) ROS 2 message package for the B to C interface
        robbie-lib-py          
          emotion/          So services getting an emotion state as messages, use unified emotion code (ie: AVD -> isHappy())
          relm/
        robbie-lib-rs       (synced agentic port of robbie-lib-py)
          emotion/
          relm/
        robbie-lib-test     Shared test data (so agentic porting is proven correct) 

      agent/                (layer a) one folder per container, any language
        llm/                Layer A: agent loop and llama.cpp client
        search/             LangChain to /data

      services/             (layer b) one folder per container, any language
        core/               state, mood, relationships, scheduler, policy gate
        hearing/            mic, voice activity, speech recognition, who said what
        vision/             camera, face detection and identity
        voice/              TTS (MaryTTS) and beeps
        memory/             memory store, redaction, audit log  (separate to /data)
        mcp/                MCP servers
        ros_bridge/         the single ROS 2 node that talks to Layer C

      deploy/
        compose.local.yaml    everything on one machine
        compose.backend.yaml  backend services
        compose.pi.yaml       services on the robot's Pi

      scripts/
        unit_test.py        # every service has a justfile, this  "just test", this script iterates . 

      testing/              
        integration_tests/  (just test)
        layer_c_robot/      a fake Layer C hor demo/humans, (Rerun + web view of robbie) using Python look_around  
        layer_c_text/       a super simple fake Layer C, for dev/ai, that output events to stdout/stderr
        evals/              Inspect AI suites, ethics scenarios, synthetic data (just vet)
        service_proforma    What a service container should look like, and testing to check it starts/stops etc.


# Services

Services all provide a justfile

Dockerfile will have

    ENTRYPOINT ["just"]
    CMD ["serve"]

Justfile will have  

    default: serve
    setup:    # For those rare times when actions genuinely need to be taken after docker creates the container.
    test:     # run unit tests
    serve:    # run the service
    vet:      # run CI tests

