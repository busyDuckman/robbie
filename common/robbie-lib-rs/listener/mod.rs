//! The IRELM listener library: consumes IRELM, co-ordinates TTS, plays the audio and sends
//! the messages (see docs/relm.md). The listener CLI is bin/listener.rs.

pub mod audio;
pub mod beep;
pub mod chunk;
pub mod config;
pub mod device;
pub mod engine;
pub mod irelm;
pub mod marytts;
pub mod messages;
pub mod player;
pub mod post;
pub mod speaker;

pub use config::{Config, Vad};
pub use irelm::{IrelmError, Message};
pub use player::{Listener, Settings, Status};
