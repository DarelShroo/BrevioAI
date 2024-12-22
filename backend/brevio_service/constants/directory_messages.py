class DirectoryMessages:
    # Mensajes de éxito
    SUCCESS_FOLDER_CREATED = "Successfully created the directory '{}'."
    SUCCES_DELETION = "Successfully deleted the directory '{}'."
    SUCCESS_FILE_DELETED = "Successfully deleted the file '{}'."

    # Mensajes de error relacionados con carpetas
    ERROR_FOLDER_ALREADY_EXISTS = "The directory '{}' already exists."
    ERROR_FAILED_TO_CREATE_FOLDER = "Creation of the directory '{}' failed: {}."
    ERROR_FOLDER_NOT_FOUND = "The directory '{}' was not found."
    ERROR_DELETION_FAILED = "Deletion of the directory '{}' failed: {}."

    # Mensajes de error relacionados con archivos
    ERROR_FILE_NOT_FOUND = "The file '{}' was not found."
    ERROR_PERMISSION_DENIED = "Permission denied to delete the file '{}'."
