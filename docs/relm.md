# Robbie's Expressive Language Model (RELM)

This is a pipeline for letting an LLM "script" (as in a play) robot dialogue and expression.

**What RELM is not:**
It's not an alternative to MCP (it does not govern broader robot behaviour), it's only concerned with emotive expression of dialogue.  RELM does not DIRECTLY do TTS, or move servos, or change LED colors etc.

**What RELM does:**
  - It informs the LLM what __named expressions__ are possible (but not how they are shown).
  - It takes LLM output using the  __named expressions__ (RELM) and converts it to a structured markup (IRELM).
  - your robot then needs to implement an IRELM listener and you're good to go.

    RELM (from llm) -> IRELM (relm.rs) ->  listener (output TTS/ROS messages/EmotionML/SSML/whatever you need).

**usage:**
You define:
    A) a RELM markup set
    B) a table to convert your RELM set to IRELM
    C) code to map IRELM to actions your robot will take.

This is RELM, what the llm outputs:

    <happy> She asked me to buy <widen_eyes><emphasis>roses</emphasis></widen_eyes></happy>

This is the RELM to Intermediate RELM (IRELM) table. The table is YAML (Robbie's is config/relm_table.yaml).

        # Macro: IRELM
        p: '<PAUSE duration="0.5"/>'           # paragraph pause
        pleasant: '<VAD v="4" a="3" d="3">'
        happy: '<VAD v="4" a="4" d="3">'
        ecstatic: '<VAD a="5" d="5">'
        emphasis: '<PROSODY s="0.6" v="1.5" p="0.75">'
        widen_eyes: '<MESSAGE sub="eyes" action="widen(0.8)"/>'
        /widen_eyes: '<MESSAGE sub="eyes" action="widen(None)"/>'


so the RELM message (llm side)

        <happy> She asked me to buy <widen_eyes><emphasis>roses</emphasis></widen_eyes></happy>

expands to (llm side)

        <IRELM>
        <VAD v="4" a="4" d="3"> She asked me to buy <MESSAGE sub="eyes" action="widen(0.8)" id="123456"/>
        <PROSODY s="0.6" v="1.5" p="0.75">roses</PROSODY><MESSAGE sub="eyes" action="widen(None)" id="123456" close="true"/></VAD>
        </IRELM>


Alternative --stateless
        
        <VAD v="4" a="4" d="3"/>
        She asked me to buy 
        <MESSAGE sub="eyes" action="widen(0.8)" id="123456"/>
        <PROSODY s="0.6" v="1.5" p="0.75"/>
        roses
        <PROSODY p="none" s="none" r="none" v="none"/>
        <MESSAGE sub="eyes" action="widen(None)" id="123456" close="true"/>
        <VAD v="none" a="none" d="none"/>


# IRELM spec

IRELM is XML. A message is wrapped in <IRELM> ... </IRELM> (unless stateless), params are attributes, and text is escaped as XML (e.g. &amp; and &lt;).
Commands that are not spans (MESSAGE, BEEP, AUDIO, PAUSE) are self-closing tags, e.g. <PAUSE duration="0.5"/>.

VAD and PROSODY params are optional. A missing param means "none".

**"none" means the enclosing value still applies.**
  - Inside another span, the value from the enclosing span is kept.
    e.g. <VAD v="4" a="4" d="3"> ... <VAD a="5"> ... </VAD> ... </VAD> gives v=4, a=5, d=3 for the inner span.
  - With no enclosing span, nothing in RELM constrains the param, so the listener uses its own state (e.g. a mood).
  - In the macro table this lets an expression blend with the mood, e.g. <VAD a="5"> sets arousal only.

  - VAD  (valence, arousal, dominance) 
    - params aliased to (v, a, d)
    - scale is 1 to 5, 3 being neutral.
     
  - PROSODY (pitch, speed, range, volume)
    - params aliased to (p, s, r, v)
    - 1.0 means 100% of the system's current configuration.
    - the values are multipliers. So s=0.8 means 20% slower.

  - MESSAGE (sub, action)
    - sends a message to other parts of the robot.
    - the only command where the closing tag can be specified
    - sub and action are arbitrary strings. Whatever your robot cares to dispatch.
      "sub" could be read as "subject", or "subscriber"
    - does not block speech
    - a macro with a close (e.g. widen_eyes and /widen_eyes) gives its messages an id. The close
      message carries the same id and close="true". This lets a listener keep a list of started
      messages awaiting a close.

  - BEEP (melody)
    - param is a melody: a semicolon separated list of "NOTE,DURATION", e.g. "C4,0.1; E4,0.1; G4,0.1; C5,0.1"
    - NOTE is a letter (A-G), an optional sharp (#) or flat (b), and an octave (0-8), e.g. C#4, Eb4.
    - R in place of a NOTE is a rest, e.g. "R,0.125".
    - DURATION is in seconds.
    - blocks speech

  - AUDIO (file_name)
    - plays a specified audio file
    - param is the file name, or a key, your listener decides what to do with it.
    - blocks speech

  - PAUSE (duration)
    - param is a duration in seconds
    - blocks speech

  - VOICE (voice, locale)
    - changes voice for a bit, as in to imitate or help with storytelling.
    - params are a "voice" name and a "locale", tune it to match your TTS setup.
    - this is not where you configure the default voice, it's for adopting a temporary voice.
    - locale is only used as a param passed to the listener. It's not used in relation to AS.
    - VOICE is a span: the closing tag (handled by the stack) returns to the previous voice.
      In stateless mode the close is sent as <VOICE voice="none" locale="none"/>.
  
  - AS (format, locale) 
    - __format__ is one of datetime|number|digits|characters|unit|currency
      - datetime: "1234" becomes "twelve thirty four"  (like a date)
                 "14:30" becomes "two thirty p m".
                 (etc)
      - currency: $12.50 becomes "twelve dollars fifty cents".
      - unit:  "15s"  becomes "fifteen seconds"
    - __locale__ is for overriding the locale, otherwise as per --locale, or LOCALE as defined in env.
                unaffected by the locale param to VOICE.
    - AS is a span around the text to expand, e.g. <AS format="datetime">14:30</AS>
    - NOTE: AS is expanded by the RELM parser, the listener does not need to understand it.
    


## macro table (what is tuned to deliver a persona)

Note: things like "/emphasis" don't need to be defined because the stack will take care of that.


**PAUSE** is the tool to sync anim ends, there are no end marks.

        # winks then continues talking
        wink: '<MESSAGE sub="eyes" action="wink(right)"/><PAUSE duration="0.2"/>'

So the wink message is sent and the delay must be calibrated to the system.


# Stateless mode

In stateless mode the stack is resolved and the listener needs to adopt the new settings as they arrive.
Getting <VAD v="none" a="none" d="none"/> means the RELM system is not placing a constraint on the displayed state. So simplistically it could mean return to default state. But perhaps there is a persistent mood modeled in the system and this would mean return to current mood. Perhaps if the system was simple and rested on neutral expression, <VAD v="none" a="none" d="none"/> will equate to <VAD v="3" a="3" d="3"/> (neutral).

Stateless output has to emit the full state at every change. For example, this RELM

        <happy> I won <ecstatic>the lottery</ecstatic> but lost the ticket </happy>

is sent in stateless mode as

        <IRELM>
        <VAD v="4" a="4" d="3"/> I won
        <VAD v="4" a="5" d="5"/> the lottery
        <VAD v="4" a="4" d="3"/> but lost the ticket
        <VAD v="none" a="none" d="none"/>
        </IRELM>

ecstatic sets no valence, so happy's v=4 still applies.
Closing ecstatic sends happy's state again, not <VAD v="none" a="none" d="none"/>, which is only sent once nothing is left on the stack.


# relm.py / relm.rs
    
Generates IRELM

        options
            --strict            Refuse bad RELM output, otherwise best effort conversion.
            --stateless         emit IRELM without any nesting (stack), so the listener can be simplified
            --table             The RELM to IRELM table
            --interactive       RELM on stdin -> IRELM on stdout
            --locale            locale for AS
            --serve <port>      RESTful API endpoint


#  listener_lib.rs  (lib)
#  listener.rs          (cli)

Consumes IRELM, co-ordinates TTS, plays resulting audio.

The library of common operations if you want to make your own listener, otherwise the CLI should be fine.


The CLI chunks the IRELM, gets wavs from tts services, schedules audio playback (using kira) and actions.

    CLI options
       --no-marks         # don't use marks 
       --device           # playback device (auto detect otherwise) can be a file.

       --tts-engine=<?>   # one of marytts|debug|TODO
       --tts-url

       --audio-dir=<?>    # audio files live here

       --beep-post=<?>    # post-processing for beep audio.
       --play-post=<?>    # post-processing for audio files. 
       --tts-post=<?>     # post-processing on the tts (done by the listener on the returned wave form)

       --interactive      # IRELM on stdin
       --serve <port>     # API (see doco).

       --allow-message-interrupt   # on interrupt, do not send the closes of started messages

       --message-url=<?>      # where messages go, the scheme picks the protocol (see message targets)
       --message-early=<?>    # if possible, messages are sent this many ms early to compensate for latency.

The CLI will always handle MESSAGE BEEP AUDIO internally
PAUSE VOICE PROSODY VAD  may or may not work with the tts engine specified.

IMPLEMENTATION NOTE: marytts will use MaryXML as the transport format.

# configuration

There is a listener.yaml to config the software.

It has :
  - VAD to prosody mapping   (many services wont support VAD type things directly or well)
  - the starting mood, until one is set by the API


# Audio post options

Each post option is an ffmpeg -af filter string, passed through as-is, e.g. --tts-post "aecho=0.8:0.9:40:0.3".
No temporary file is needed, the wav is piped through ffmpeg:

    ffmpeg -f wav -i pipe:0 -af "<filter>" -f wav pipe:1

Leave an option out for no post-processing. Post-processing needs ffmpeg on the PATH.

# API
API is the best way to do this. -- interactive is more for testing (where device is a file).

API allows:
  - interruption.
  - mood setting (what the VAD returns to)

The API is HTTP on the --serve port.

    POST /say          body is IRELM. It is queued behind anything already playing.
                       Replies 202 once the IRELM is parsed, 400 if it is not valid IRELM.
    POST /interrupt    stops the current audio and clears the queue. Messages not yet sent are dropped,
                       except the closes of started messages (matched by id, e.g. widen(None)), which
                       are sent at once so the robot is not left mid expression.
                       --allow-message-interrupt drops those too.
    PUT  /mood         body is VAD, e.g. <VAD v="3" a="3" d="3"/>. "none" params fall back to this.
    GET  /mood         the current mood, as VAD.
    GET  /status       JSON, e.g. {"state": "speaking", "queued": 2}. state is speaking or idle.
    GET  /health       "ok".

# Message targets

--message-url says where MESSAGE goes. The scheme picks the protocol:

    stdout:                      one "sub, action" line per message (split on the first comma). For tests and piping.
    tcp://host:2000              the same lines over a TCP socket. Watch it with nc host 2000.
    mqtt://broker:1883/relm      MQTT, one topic per sub under the given topic, e.g. relm/eyes.
    ros:                         ROS 2, see below.

Robbie's own messaging layer (Zenoh or NATS, see build_plan.md) can be added as a scheme once it is chosen.
Each protocol needs a client crate, so they are added as needed.

# ROS
Sends a custom message as per:

    # RelmMessage.msg

    std_msgs/Header header   # stamp = when it should happen
    string sub
    string action

Expects one topic per "sub" (see IRELM) eg sub (/relm/eyes, /relm/head).