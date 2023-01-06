import os
import pygame
import constants as const
import enums


# File names
BUTTON_REGULAR_IMAGE = 'Button.png'
BUTTON_HOVERED_IMAGE = 'ButtonHovered.png'
BUTTON_INACTIVE_IMAGE = 'ButtonInactive.png'

PLAYER_IDLE_IMAGES = 'player/idle/player_idle.png'


def load_image(image_name: str, transparent_color: pygame.Color=None, alpha: int=None) -> pygame.Surface:
    """
    Function used to load the image from the disk to the pygame.Surface
    :param image_name: name of the file
    :param transparent_color: transparent color of the image
    :param alpha: alpha value of the image
    :return: image Surface
    """
    image = pygame.image.load(os.path.join(const.IMAGE_FOLDER, image_name))
    if transparent_color is not None:
        image.set_colorkey(transparent_color)
    if alpha is not None:
        image.set_alpha(alpha)
    return image.convert_alpha()


class Assets:
    """
    Class used to work with the images/sounds etc.
    """
    def __init__(self):
        self.images: dict[str, list[pygame.Surface]] = {}

    def load(self) -> None:
        """
        Loads the images from the disk
        :return: None
        """
        self.images["BUTTON"] = [load_image(BUTTON_REGULAR_IMAGE),
                                 load_image(BUTTON_HOVERED_IMAGE),
                                 load_image(BUTTON_INACTIVE_IMAGE)]

        self.images[enums.Animations.PLAYER_WALK] = load_image(PLAYER_IDLE_IMAGES)
        self.images[enums.Animations.PLAYER_IDLE] = load_image(PLAYER_IDLE_IMAGES)

    def get_image(self, name: str) -> pygame.Surface:
        """
        Returns the image
        :param name: name of the image
        :return: image Surface
        """
        return self.images[name][0]

    def get_images(self, name: str) -> list[pygame.Surface]:
        """
        Returns the list of images
        :param name: name of the images
        :return: list of image Surface
        """
        return self.images[name]

class SingleAnimation:
    def __init__(self, name: enums.Animations, time_per_frame=10):
        self.name = name
        self.image = const.program.assets.get_images(self.name)
        self.images = [self.image.subsurface(pygame.Rect(x*const.IMAGE_WIDTH, 0, const.IMAGE_WIDTH, const.IMAGE_WIDTH)) for x in (range(self.image.get_width() // const.IMAGE_WIDTH))]
        self.image_index = 0
        self.time_per_frame = time_per_frame
    
    def animate(self):
        self.image_index += 1
        if self.image_index + 1 >= len(self.images) * self.time_per_frame:
            self.image_index = 0
        return self.images[self.image_index // self.time_per_frame]

class Animation:
    def __init__(self, animations: dict[enums.Animations, SingleAnimation]):
        self.animations: dict[str, SingleAnimation] = animations
        self.current_animation = ""

    def set_current_animation(self, name: str):
        self.current_animation = name

    def get_current_image(self):
        anim = self.animations[self.current_animation]
        return anim.images[anim.image_index]
        
    def play_current_animation(self):
        return self.animations[self.current_animation].animate()
