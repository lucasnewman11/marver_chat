# Sales Call Transcripts RAG System

This is a specialized Retrieval-Augmented Generation (RAG) system designed to work with all the sales call transcripts in your Google Drive.

## Features

- **Automatic Document Loading**: Automatically loads all 49 sales call transcripts from your Google Drive
- **Local Caching**: Saves all documents locally to enable fast repeated querying
- **Parallel Downloads**: Uses multithreading to download files faster
- **Smart Document Selection**: Selects documents to fit within context limits
- **Interactive Interface**: Simple command-line interface for querying the data

## How to Use

1. Run the RAG system:
   ```bash
   python -m src.rag_all_files
   ```

2. The system will:
   - Download all sales call transcripts from Google Drive
   - Save them to a local cache folder (`all_transcripts`)
   - Present you with an interactive menu

3. From the menu, you can:
   - Ask questions about the transcripts
   - Reload files from Google Drive if they've been updated
   - Exit the system

## Example Questions

Here are some example questions you can ask:

- "What are the common objections mentioned in these sales calls?"
- "What pricing information is discussed in these transcripts?"
- "What product features are most frequently highlighted?"
- "What customer pain points are mentioned most often?"
- "What follow-up actions were promised in these calls?"

## Technical Notes

- Uses Google Drive API to access files
- Uses Anthropic's Claude 3.7 Sonnet (2025-02-19) for answering questions
- No need for external embedding providers; documents are provided directly to Claude
- Automatic document selection to fit within Claude's context window

## Troubleshooting

If you encounter any issues:

1. Check that the `.env` file contains your Anthropic API key
2. Verify that the service account has access to the sales call transcripts
3. If documents don't appear to be loading, try option 2 to force reload from Google Drive

## Extending the System

This system could be enhanced with:
- Semantic search for better document selection
- Web UI instead of command-line interface
- Document categorization and filtering options
- Support for additional file types beyond Google Docs