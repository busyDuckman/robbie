//! RELM: turn LLM output written with named expressions into IRELM. See docs/relm.md.

mod convert;
pub(crate) mod markup;
pub mod say_as;
pub(crate) mod table;

pub use convert::{convert, Converter, Options};
pub use markup::{ErrorKind, RelmError};
pub use table::{Command, Macro, Table};
