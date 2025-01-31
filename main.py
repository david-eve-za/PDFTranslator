import argparse
import sys

from MainController import MainController


def main():
    """
    Main function to process documents with configurable options.
    """
    # Create the parser
    parser = argparse.ArgumentParser(description="Script to process documents with configurable options.")

    # Mandatory argument for the path
    parser.add_argument(
        "path",
        type=str,
        help="Path to the file or directory to be processed."
    )

    # Model with predefined choices and a default value
    parser.add_argument(
        "-m", "--model",
        type=str,
        choices=["qwen2.5:32b", "gpt-4", "llama2-70b", "bloomz-176b", "deepseek-r1:32b","deepseek-r1:8b","granite3-dense:8b"],
        default="qwen2.5:32b",
        help="Model to use for processing (default: qwen2.5:32b)."
    )

    # Optional output path with a default value
    parser.add_argument(
        "-o", "--output_path",
        type=str,
        default="translated",
        help="Path where the processed output will be saved (default: translated)."
    )

    # Source and target languages with default values
    parser.add_argument(
        "--source_language",
        type=str,
        default="English",
        help="Source language of the text (default: English)."
    )
    parser.add_argument(
        "--target_language",
        type=str,
        default="Spanish",
        help="Target language for translation (default: Spanish)."
    )

    # Tokenization size with a default value
    parser.add_argument(
        "--token_size",
        type=int,
        default=1000,
        help="Maximum number of tokens per processing block (default: 1000)."
    )

    # Set only translation mode
    parser.add_argument(
        "--only_translation",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable translation mode (default: true)."
    )

    # Parse arguments
    args = parser.parse_args()

    # Display the obtained values
    print("\n--- Entered Parameters ---")
    print(f"Input path: {args.path}")
    print(f"Selected model: {args.model}")
    print(f"Output path: {args.output_path}")
    print(f"Source language: {args.source_language}")
    print(f"Target language: {args.target_language}")
    print(f"Tokenization size: {args.token_size}")
    print(f"Only translation mode: {args.only_translation}")

    # Request confirmation
    # confirmation = input("\nAre these parameters correct? (y/n): ").strip().lower()
    # if confirmation != 'y':
    #     print("Operation canceled by the user.")
    #     sys.exit(0)

    print("Parameters confirmed. Starting the processing...")
    # Add the code here to continue with the file processing
    controller = MainController(input_dir=args.path, model_name=args.model, token_size=args.token_size,
                                output_dir=args.output_path, source_language=args.source_language,
                                target_language=args.target_language, only_translation=args.only_translation)
    controller.process_pdfs()


if __name__ == "__main__":
    main()
