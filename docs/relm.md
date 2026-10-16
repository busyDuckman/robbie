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

This is the RELM to Intermediate RELM (IRELM) table.

        # Macro,   IRELM
        p           = <PAUSE 0.5>           # paragraph pause
        pleasant    = <VAD 4, 3, 3>
        happy       = <VAD 4, 4, 3>
        ecstatic    = <VAD a=5, d=5>
        emphasis    = <PROSODY s=0.6, v=1.5, p=0.75>
        widen_eyes  = <MESSAGE sub="eyes", action ="widen(0.8)">
        /widen_eyes  = <MESSAGE sub="eyes", action ="widen(None)">


so the RELM message (llm side)

        <happy> She asked me to buy <widen_eyes><emphasis>roses</emphasis></widen_eyes></happy>

expands to (llm side)

        <VAD 4, 4, 3> She asked me to buy <MESSAGE sub="eyes", action ="widen(0.8)">
        <PROSODY s=0.6, v=1.5, p=0.75>roses</PROSODY><MESSAGE sub="eyes", action ="widen(None)"></VAD>


Alternative --stateless
        <VAD 4, 4, 3>
        She asked me to buy 
        <MESSAGE sub="eyes", action ="widen(0.8)">
        <PROSODY s=0.6, v=1.5, p=0.75>
        roses
        <PROSODY None>
        <MESSAGE sub="eyes", action ="widen(None)">
        <VAD None>


# IRELM spec

VAD and PROSODY params are optional. A missing param takes the default for that command.

  - VAD  (valence, arousal, dominance) 
    - default is (3,3,3)
    - params aliased to (v, a, d)
    - scale is 1 to 5, 3 being neutral.
     
  - PROSODY (pitch, speed, range, volume)
    - params aliased to (p, s, r, v)
    - default is (1.0, 1.0, 1.0, 1.0) which means 100% of the system's current configuration.
    - the values are multipliers. So s=0.8 means 20% slower.

  - MESSAGE (sub, action)
    - sends a message to other parts of the robot.
    - the only command where the closing tag can be specified
    - sub and action are arbitrary strings. Whatever your robot cares to dispatch.
      "sub" could be read as "subject", or "subscriber"
    - does not block speech

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

  - PAUSE
    - param is a duration in seconds
    - blocks speech

  - VOICE
    - changes voice for a bit, as in to imitate or help with storytelling.
    - params are a "voice" name and a "locale", tune it to match your TTS setup.
    - this is not where you configure the default voice, it's for adopting a temporary voice.
    - locale is only used as a param passed to the listener. It's not used in relation to AS.
    - VOICE is a span: the closing tag (handled by the stack) returns to the previous voice.
      In stateless mode the close is sent as <VOICE None>.
  
  - AS (format, locale) 
    - __format__ is one of datetime|number|digits|characters|unit|currency
      - datetime: "1234" becomes "twelve thirty four"  (like a date)
                 "14:30" becomes "two thirty p m".
                 (etc)
      - currency: $12.50 becomes "twelve dollars fifty cents".
      - unit:  "15s"  becomes "fifteen seconds"
    - __locale__ is for overriding the locale, otherwise as per --locale, or LOCALE as defined in env.
                unaffected by the locale param to VOICE.
    - NOTE: AS is expanded by the RELM parser, the listener does not need to understand it.
    


## macro table (what is tuned to deliver a persona)

Note: things like "/emphasis" don't need to be defined because the stack will take care of that.


**PAUSE** is the tool to sync anim ends, there are no end marks.

        # winks then continues talking
        wink  = <MESSAGE sub="eyes", action ="wink(right)"> <PAUSE 0.2>

So the wink message is sent and the delay must be calibrated to the system.


# Stateless mode

In stateless mode the stack is resolved and the listener needs to adopt the new settings as they arrive.
Getting <VAD None> means the RELM system is not placing a constraint on the displayed state. So simplistically it could mean return to default state. But perhaps there is a persistent mood modeled in the system and this would mean return to current mood. Perhaps if the system was simple and rested on neutral expression, <VAD None> will equate to <VAD 3, 3, 3> (neutral).

Stateless output has to emit the full state at every change. For example, this RELM

        <happy> I won <ecstatic>the lottery</ecstatic> but lost the ticket </happy>

is sent in stateless mode as

        <VAD 4, 4, 3>  I won
        <VAD 3, 5, 5>  the lottery
        <VAD 4, 4, 3>  but lost the ticket
        <VAD None>

Closing ecstatic sends happy's state again, not <VAD None>. <VAD None> is only sent once nothing is left on the stack.


# relm.py / relm.rs
    
Generates IRELM

        options
            --strict            Refuse bad RELM output, otherwise best effort conversion.
            --stateless         emit IRELM without any nesting (stack), so the listener can be simplified
            --table             The RELM to IRELM table
            --interactive       RELM on stdin -> IRELM on stdout
            --locale            locale for AS
            --serve <port>      RESTful API endpoint

            --vad_to_emotionml     maps VAD to EmotionML, for systems that are happy with that directly.
            --vad_to_ssml          approximates VAD with ssml <prosody> (can't use with --vad_to_emotionml)

            --prosody_to_ssml      maps PROSODY to ssml <prosody>
            --voice_to_ssml        maps VOICE to ssml <voice> and xml:lang
            --pause_to_ssml        maps PAUSE to ssml <break>
            --message_to_ssml      maps MESSAGE to ssml <mark>
            --audio_to_ssml        maps AUDIO to ssml <audio>
            --beep_to_ssml         maps BEEP to ssml <audio>, by rendering the melody to a temporary wav file
            
            --as_to_ssml           disable internal AS, pass via ssml <say-as>

When --vad_to_ssml and --prosody_to_ssml are both used, relm.py resolves VAD and PROSODY to the effective prosody.


# listener_lib.py / listener_lib.rs  (lib)
# listener.py / listener.rs          (cli)

Consumes IRELM

Library of common operations to help make a listener (and cli that may work for many cases)

    CLI options
        


