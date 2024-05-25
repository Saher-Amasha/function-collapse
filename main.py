"""
program that takes the path to a folder contating tiles and 
using wave function collapse creates a larger image from that
"""

from dataclasses import dataclass
from functools import lru_cache
import json
import random
from enum import Enum
from PIL import Image


class ImpossibleGrid(Exception):
    """
    raised when there isnt any tile that makes the grid workm
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class TileEdges(Enum):
    """
    All possible Tile Edges
    """

    TOP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

    @staticmethod
    def get_oposite(edge_dir: int):
        """
        returns the opposite Tile edge
        """
        return TileEdges((edge_dir + 2) % 4)


@dataclass
class Tile:
    """A single Tile"""

    id: int
    path: str
    edges: list
    rotation: int = 0

    def get_edge(self, edge_dir: TileEdges):
        """
        gets Tile edge Connections
        """
        return self.edges[edge_dir.value]

    def rotate(self, rotation: int):
        """
        Returns a new rotated tile
        """
        new_edges = self.edges.copy()
        for _ in range(rotation):
            new_edges.insert(0, new_edges.pop(-1))
        return Tile(
            self.id + rotation,
            self.path,
            new_edges,
            rotation,
        )


@dataclass
class EntropyPoint:
    """A single entropy point"""

    possible_tiles: set
    tile: Tile = None

    def collapsed(self):
        """
        returns true if cell is collapesd
        """
        return self.tile is not None

    def set_tile(self, tile: Tile):
        """
        sets the cells tile
        """
        self.tile = tile


class Grid:
    """A grid"""

    def __init__(self, file, tile_width=10, tile_height=10) -> None:
        tile_id = 0
        self.possible_tiles = []

        # Open config file
        with open(file + "/data.json", "r", encoding="utf-8") as f:
            config = json.loads(f.read())

        # Load rotations
        rotations = config["rotations"]
        tiles = config["rotations"].keys()

        # For every tile create a tile class for it and for its rotations and add
        # Them to possible tiles
        for tile in tiles:
            current_tile = Tile(
                id=tile_id, path=f"{file}/{tile}.png", edges=config[tile]
            )

            self.possible_tiles.append(current_tile)

            tile_id += 1
            for rotation in rotations[tile]:
                self.possible_tiles.append(current_tile.rotate(rotation))
                tile_id += 1

        self.pixel_width, self.pixel_height = Display.load_image(
            self.possible_tiles[0].path
        ).size
        # Initialize grid to be full of cells that have all tiles as possible tiles
        self._inner_vals = [
            [
                EntropyPoint(possible_tiles=set(range(tile_id)))
                for _ in range(tile_width)
            ]
            for _ in range(tile_height)
        ]

    def advance(self):
        """
        Take one step foroward
        """
        max_collapsed_num = 0

        for x, row in enumerate(self._inner_vals):
            for y, tile in enumerate(row):
                # If collapsed continue
                if tile.collapsed():
                    continue

                # Get all possible neighbors and the edge that will intersect that neighbor
                poses = [
                    [x, y - 1, TileEdges.TOP],
                    [x + 1, y, TileEdges.RIGHT],
                    [x, y + 1, TileEdges.DOWN],
                    [x - 1, y, TileEdges.LEFT],
                ]
                # Keep track of the cell with the most collapsed neighbors
                current_collapsed_neighbors = 0
                for pos_x, pos_y, direction in poses:
                    if not 0 <= pos_x <= len(self._inner_vals[0]) - 1:
                        current_collapsed_neighbors += 1
                        continue
                    if not 0 <= pos_y <= len(self._inner_vals) - 1:
                        current_collapsed_neighbors += 1
                        continue

                    neighbor = self._inner_vals[pos_x][pos_y]

                    # For every direction remove any tile that doesnt matche this neighbor
                    if neighbor.collapsed():
                        current_collapsed_neighbors += 1

                        for i in self.possible_tiles:
                            if neighbor.tile.get_edge(
                                TileEdges.get_oposite(direction.value)
                            )[::-1] != i.get_edge(direction):
                                if i.id in tile.possible_tiles:
                                    tile.possible_tiles.remove(i.id)

                if len(tile.possible_tiles) == 1:
                    # if we only have one option that is possible (best case)
                    # we set the tile for the cell and continue
                    tile.set_tile(self.possible_tiles[next(iter(tile.possible_tiles))])
                    return True
                # Update maximun collapsed in the case where no one tile
                # Has only one possibility we will use that value there
                if current_collapsed_neighbors > max_collapsed_num:
                    max_collapsed_num = current_collapsed_neighbors
                    max_x, max_y = x, y

        # we exitied the loop and no one cell had only one tile option
        if max_collapsed_num != 0:
            # We take the cell with the least possible options
            mcl = self._inner_vals[max_x][max_y]

            if len(mcl.possible_tiles) == 0:
                raise ImpossibleGrid()

            # and choose one random tile from there to be the tile for that cell
            self._inner_vals[max_x][max_y].set_tile(
                self.possible_tiles[random.choice(list(mcl.possible_tiles))]
            )
            return True
        return False


class Display:
    """
    Class responsible for displaying grid
    """

    def __init__(self, grid: Grid) -> None:
        self._inner_vals = grid._inner_vals
        self.tile_pixel_height = grid.pixel_height
        self.tile__pixel_width = grid.pixel_width
        self.grid_height = len(self._inner_vals[1])
        self.grid_width = len(self._inner_vals[0])

    @lru_cache
    @staticmethod
    def load_image(path: str):
        """
        Loads image and caches it
        """
        return Image.open(path)

    @lru_cache
    @staticmethod
    def load_and_rotate_image(path: str, rotation: int):
        """
        Loads image rotatets it and caches it
        """
        im = Display.load_image(path)
        if rotation == 0:
            return im
        return im.rotate(
            rotation,
            expand=1,
        )

    def generate_image_from_grid(self):
        """
        Generates an image from input grid
        """
        new_im = Image.new(
            "RGB",
            (
                self.tile_pixel_height * self.grid_width,
                self.tile_pixel_height * self.grid_height,
            ),
        )
        for i in range(
            0, self.tile_pixel_height * self.grid_width, self.tile_pixel_height
        ):
            for j in range(
                0, self.tile_pixel_height * self.grid_width, self.tile_pixel_height
            ):
                current_cell = self._inner_vals[int(i / self.tile_pixel_height)][
                    int(j / self.tile_pixel_height)
                ]
                if current_cell.tile is None:
                    path = "default_tile.png"
                    rotation = 0

                else:
                    path = current_cell.tile.path
                    rotation = 360 - current_cell.tile.rotation * 90

                im = Display.load_and_rotate_image(path, rotation)
                im.thumbnail((self.tile_pixel_height, self.tile_pixel_height))
                new_im.paste(im, (i, j))
        im.show()
        new_im.convert("RGB").save("geeks.jpg")


def main(
    path: str,
    tile_width: int,
    tile_height: int,
    diplay_per_image: bool = True,
    verbose: bool = True,
):
    """
    Main function
    """
    grid = Grid(path, tile_width, tile_height)
    changing = True
    while changing:
        try:
            changing = grid.advance()
        except ImpossibleGrid:
            if verbose:
                print("Grid was impossible retring")
            grid = Grid(path, tile_width, tile_height)
        if diplay_per_image:
            Display(grid).generate_image_from_grid()
    if not diplay_per_image:
        Display(grid).generate_image_from_grid()


if __name__ == "__main__":
    path = "./tiles/circuit_coding_train"
    tile_width = 10
    tile_height = 10
    diplay_per_image = True
    verbose = True
    main(path, tile_width, tile_height, diplay_per_image, verbose)
