#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import cv2
from PIL import Image


DICT_NAME_TO_ID = {
    "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
    "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
    "DICT_4X4_250": cv2.aruco.DICT_4X4_250,
    "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
    "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
    "DICT_5X5_250": cv2.aruco.DICT_5X5_250,
    "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
    "DICT_6X6_100": cv2.aruco.DICT_6X6_100,
    "DICT_6X6_250": cv2.aruco.DICT_6X6_250,
}

A4_MM = (210.0, 297.0)


def mm_to_px(length_mm, dpi):
    return int(round(length_mm / 25.4 * dpi))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate a printable ChArUco board for D435i-Panda hand-eye calibration."
    )
    parser.add_argument("--squares-x", type=int, default=5, help="Number of chessboard squares along X.")
    parser.add_argument("--squares-y", type=int, default=7, help="Number of chessboard squares along Y.")
    parser.add_argument(
        "--square-length-mm",
        type=float,
        default=30.0,
        help="Chessboard square length in millimeters.",
    )
    parser.add_argument(
        "--marker-length-mm",
        type=float,
        default=22.0,
        help="ArUco marker side length in millimeters.",
    )
    parser.add_argument(
        "--dictionary",
        choices=sorted(DICT_NAME_TO_ID),
        default="DICT_5X5_100",
        help="Predefined ArUco dictionary.",
    )
    parser.add_argument("--dpi", type=int, default=300, help="Output image DPI.")
    parser.add_argument(
        "--page-width-mm",
        type=float,
        default=A4_MM[0],
        help="Page width in millimeters.",
    )
    parser.add_argument(
        "--page-height-mm",
        type=float,
        default=A4_MM[1],
        help="Page height in millimeters.",
    )
    parser.add_argument(
        "--margin-mm",
        type=float,
        default=15.0,
        help="White margin around the board in millimeters.",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path("/home/mfj/biaoding/boards/charuco_a4_5x7_30mm"),
        help="Output path prefix without extension.",
    )
    return parser


def main():
    args = build_parser().parse_args()

    if args.marker_length_mm >= args.square_length_mm:
        raise ValueError("marker-length-mm must be smaller than square-length-mm.")

    board_width_mm = args.squares_x * args.square_length_mm
    board_height_mm = args.squares_y * args.square_length_mm
    usable_width_mm = args.page_width_mm - 2.0 * args.margin_mm
    usable_height_mm = args.page_height_mm - 2.0 * args.margin_mm

    if board_width_mm > usable_width_mm or board_height_mm > usable_height_mm:
        raise ValueError(
            "Board does not fit on the page with the requested margins. "
            f"Board={board_width_mm:.1f}x{board_height_mm:.1f} mm, "
            f"usable={usable_width_mm:.1f}x{usable_height_mm:.1f} mm."
        )

    page_width_px = mm_to_px(args.page_width_mm, args.dpi)
    page_height_px = mm_to_px(args.page_height_mm, args.dpi)
    board_width_px = mm_to_px(board_width_mm, args.dpi)
    board_height_px = mm_to_px(board_height_mm, args.dpi)

    dictionary = cv2.aruco.getPredefinedDictionary(DICT_NAME_TO_ID[args.dictionary])
    board = cv2.aruco.CharucoBoard(
        (args.squares_x, args.squares_y),
        args.square_length_mm / 1000.0,
        args.marker_length_mm / 1000.0,
        dictionary,
    )

    board_image = board.generateImage((board_width_px, board_height_px), marginSize=0, borderBits=1)
    page_image = 255 * (board_image[:1, :1].copy())
    page_image = page_image.repeat(page_height_px, axis=0).repeat(page_width_px, axis=1)

    offset_x = (page_width_px - board_width_px) // 2
    offset_y = (page_height_px - board_height_px) // 2
    page_image[offset_y : offset_y + board_height_px, offset_x : offset_x + board_width_px] = board_image

    output_prefix = args.output_prefix
    output_prefix.parent.mkdir(parents=True, exist_ok=True)

    png_path = output_prefix.with_suffix(".png")
    pdf_path = output_prefix.with_suffix(".pdf")
    meta_path = output_prefix.with_suffix(".json")

    cv2.imwrite(str(png_path), page_image)

    pil_image = Image.fromarray(page_image)
    pil_image.save(str(pdf_path), "PDF", resolution=args.dpi)

    metadata = {
        "board_type": "charuco",
        "dictionary": args.dictionary,
        "squares_x": args.squares_x,
        "squares_y": args.squares_y,
        "square_length_mm": args.square_length_mm,
        "marker_length_mm": args.marker_length_mm,
        "page_width_mm": args.page_width_mm,
        "page_height_mm": args.page_height_mm,
        "margin_mm": args.margin_mm,
        "dpi": args.dpi,
        "board_width_mm": board_width_mm,
        "board_height_mm": board_height_mm,
        "png_path": str(png_path),
        "pdf_path": str(pdf_path),
        "print_note": "Print at 100% scale with no fit-to-page resizing.",
    }
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, ensure_ascii=False)

    print(f"Generated PNG: {png_path}")
    print(f"Generated PDF: {pdf_path}")
    print(f"Generated metadata: {meta_path}")


if __name__ == "__main__":
    main()
