## Handle Documents sent on WhatsApp (LOI and signature)

Steps:

1. Initial Message Validation

   - Validate incoming message contains document
   - Extract document metadata (mime_type, filename)
   - Return error if document missing

2. File Type Validation

   - Confirm file is PDF or JSON format
   - Extract document ID for processing
   - Return error if invalid file type

3. File Preparation

   - Create upload directory if not exists
   - Generate secure temporary filename
   - Build complete file path for storage

4. Document Download Process

   - Retrieve document URL from Facebook Graph API
   - Validate media URL exists and is accessible
   - Download file content
   - Save file to temporary location

5. PDF File Handling

   - Store PDF path and filename in user storage
   - Check for existing JSON file
     - If JSON exists: Move to verification
     - If no JSON: Send "awaiting JSON" message

6. JSON File Handling

   - Store JSON path and filename in user storage
   - Check for existing PDF file
     - If PDF exists: Move to verification
     - If no PDF: Send "awaiting PDF" message

7. Verification Process

   - Read and parse JSON file content
   - Extract signature data
   - Perform signature verification
   - Generate verification result message

8. Cleanup Operations

   - Remove PDF file from disk
   - Remove JSON file from disk
   - Clear user data from storage
   - Return status message

9. Error Handling

   - Log detailed error information
   - Clean up any stored files
   - Remove user data from storage
   - Send error message to user

10. Response Generation

    - Format appropriate status message
    - Send formatted message to user
    - Ensure proper message delivery

## Pseudo code

```
Function handle_document_message(message, wa_id, name):
    // Initial validation
    IF message doesn't contain document:
        RETURN error "Send both PDF and signature.json"

    // Extract document info
    document = get document from message
    mime_type = get mime_type from document
    filename = get filename from document (default: "document.pdf")

    // Validate file type
    IF not (PDF or JSON file):
        RETURN error "Send either PDF or signature.json"

    TRY:
        // Setup file handling
        document_id = get ID from document
        create upload folder if not exists
        generate secure temp filename and path

        // Download file
        get document URL from Facebook API
        download file content
        save file to temp path

        IF file is PDF:
            store PDF path and filename in user_files[wa_id]

            IF user already has JSON file:
                RETURN verify_and_cleanup(wa_id, json_path, pdf_path)
            ELSE:
                RETURN message "PDF received, send signature.json"

        ELSE (file is JSON):
            store JSON path and filename in user_files[wa_id]

            IF user already has PDF file:
                RETURN verify_and_cleanup(wa_id, json_path, pdf_path)
            ELSE:
                RETURN message "JSON received, send PDF"

    CATCH any error:
        cleanup all files for this user
        log error
        RETURN error message to user

Function verify_and_cleanup(wa_id, json_path, pdf_path):
    TRY:
        read and parse JSON file
        verify signature using verify_object_signature()
        prepare success/failure message
    CATCH:
        prepare error message
    FINALLY:
        delete PDF file
        delete JSON file
        remove user data from user_files
        RETURN message to user
```

# Pending work

1. Implement guided response for introduction phase --> refer to Miro
   - Restrict responses to introduction phase guidelines
   - Prevent from answering abstract questions: Eg. How is the weather

# Future work (not to be focussed on now):

1. What happens if the user uploads 3 files: valid(pdf, json) & invalid(pdf or json)
2. What ahppens if the user uploads 3 files: valid(pdf, json) & photo/txt file/unsupported file type
