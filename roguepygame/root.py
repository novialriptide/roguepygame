from typing import Optional, Type, Any, Callable

import pygame
import constants as const
import game


class Scene:
    """
    Class used to represent the game scene
    it is responsible for processing the events, updating the game state, and rendering the game
    """
    def __init__(self, **kwargs):
        self.program: game.Game = const.program
        self.state: dict[str, Any] = {
            'mouse_pos': (-1000, -1000)
        }

    def start(self) -> None:
        """
        Method used once after the Scene has been initialized
        :return: None
        """
        pass

    def events(self, events: list[pygame.event.Event]) -> None:
        """
        Method used to process the events returned by pygame.event.get()
        Gets called at the start of the game loop.
        Default implementation checks for QUIT event and calls events for objects
        :param events: pygame events
        :return: None
        """
        for event in events:
            if event.type == pygame.QUIT:
                self.program.quit()
        self.program.get_object_manager().object_events(events)

    def update(self) -> None:
        """
        Method used to update the game.
        Gets called after Scene.events() every iteration of game loop.
        Every Scene must implement it.
        :return: None
        """
        raise NotImplementedError(f"{self.__class__.__name__} Scene must implement update method!")

    def render(self, screen: pygame.Surface) -> None:
        """
        Method used to render the game.
        Method gets the game window as the argument.
        Gets called after Scene.update() every iteration of game loop.
        Every Scene must implement it.
        :param screen: Game window
        :return: None
        """
        raise NotImplementedError(f"{self.__class__.__name__} Scene must implement render method!")

    def end(self) -> None:
        """
        Method called before swapping to another scene.
        :return: None
        """
        pass

    def update_state(self):
        """
        Method that updates the state of the program
        :return: None
        """
        self.state['mouse_pos'] = pygame.mouse.get_pos()


class SceneManager:
    """
    Class used to manage the scenes.
    It gives the ability to swap between the scenes.
    Also contains the ObjectManager for the game.
    This object shouldn't be initialised, but rather called from the Game class.
    """
    def __init__(self):
        self.program: game.Game = const.program
        self.scene: Optional[Scene] = None
        self.object_manager: ObjectManager = ObjectManager()

    def go_to(self, scene: Type[Scene], **kwargs) -> None:
        """
        Method you should call when you want to go to another scene
        :param scene: reference to the scene you want to go to
        :param kwargs: arguments you want to pass to the new scene
        :return: None
        """
        if self.scene is not None:
            self.scene.end()
            self.object_manager.clear_objects()
        self.scene = scene(**kwargs)
        self.scene.program = self.program
        self.scene.start()


class ObjectManager:
    """
    Class used to manage the objects.
    It contains the collection of all the active objects in the scene.
    It supports creating and destroying the objects.
    It gives the ability to iterate over all objects and call important methods.
    You shouldn't create the instance of this object, but rather use the object already created in the Game class.
    """
    def __init__(self):
        self.program: game.Game = const.program
        self.objects: list[GameObject] = []

    def object_events(self, events: list[pygame.event.Event]) -> None:
        """
        Method used to call the events() method of all objects
        :param events: list of pygame events
        :return: None
        """
        self.check_clickable(events)
        for obj in self.objects:
            if callable(getattr(obj, "events", None)):
                obj.events(events)

    def object_update(self) -> None:
        """
        Method used to call the update() method of all objects
        :return: None
        """
        for obj in self.objects:
            if callable(getattr(obj, "update", None)):
                obj.update()

    def object_render(self, screen: pygame.Surface) -> None:
        """
        Method used to call the render() method of all DrawableObjects
        :param screen: game window
        :return: None
        """
        for obj in self.objects:
            if isinstance(obj, DrawableObject):
                obj.render(screen)

    def create_object(self, obj: "GameObject") -> None:
        """
        Method used to add new object to the list of objects
        :param obj: GameObject you want to add
        :return: None
        """
        self.objects.append(obj)
        self.objects.sort(key=lambda x: x.layer if hasattr(x, 'layer') else 0)

    def remove_object(self, obj: "GameObject") -> None:
        """
        Method used to remove object from the list of objects
        :param obj: GameObject you want to remove
        :return: None
        """
        self.objects.remove(obj)

    def clear_objects(self) -> None:
        """
        Method used to remove all objects from the list of objects
        :return: None
        """
        self.objects.clear()

    def check_clickable(self, events: list[pygame.event.Event]) -> None:
        """
        Method that checks if you clicked on any clickable object
        :param events: list of events
        :return: None
        """
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_position = self.program.get_scene().state['mouse_pos']
                for obj in self.objects:
                    if isinstance(obj, ClickableObject):
                        if obj.rect.collidepoint(mouse_position):
                            if event.button == 1:
                                obj.click_function()
                            if event.button == 3:
                                obj.click_function_right()


class GameObject:
    """
    Class used to represent the basic game object
    """
    def __init__(self):
        self.program: game.Game = const.program
        self.name: Optional[str] = None
        self.child_objects: dict[str, GameObject] = {}

    def add_child(self, child_obj: "GameObject", child_name: Optional[str] = None) -> None:
        """
        Method that creates the child of the GameObject
        :param child_obj: child object
        :param child_name: name of the child
        :return: None
        """
        if child_name is None:
            child_name = len(self.child_objects)
            while child_name in self.child_objects:
                child_name += 1
        self.child_objects[str(child_name)] = child_obj

    def create_object(self, name: Optional[str] = None) -> "GameObject":
        """
        Method that adds the object and its children to the ObjectManager
        :param name: name of the object
        :return: self
        """
        if name is not None:
            self.name = name
        self.program.get_object_manager().create_object(self)
        for child in self.child_objects.values():
            child.create_object()
        return self

    def destroy_object(self) -> None:
        """
        Method to remove the object from the ObjectManager
        :return: None
        """
        for child in self.child_objects.values():
            child.destroy_object()
        self.program.get_object_manager().remove_object(self)


class DrawableObject(GameObject):
    """
    Class used to represent the object that is drawn on the Scene
    Requires image and rect attributes
    """

    def __init__(self, image: pygame.Surface = None, rect: pygame.Rect = None, layer: int = 1):
        super(DrawableObject, self).__init__()
        self.image = image
        self.rect = rect
        self.layer = layer

    def render(self, screen: pygame.Surface) -> None:
        """
        Method that draws the object to the game window.
        :param screen: game window
        :return: None
        """
        screen.blit(self.image, self.rect)


class ClickableObject(DrawableObject):
    """
    Drawable object that can be clicked
    Must implement click_function()
    """
    def __init__(self):
        super(ClickableObject, self).__init__()

    def click_function(self):
        """
        Function that gets called when the object is clicked with the left mouse button
        :return: None
        """
        raise NotImplementedError(f"{self.__class__.__name__} ClickableObject must implement click_function method!")

    def click_function_right(self):
        """
        Function that gets called when the object is clicked with the right mouse button
        :return: None
        """
        pass


class Timer(GameObject):
    """
    Class used for timer
    """
    def __init__(self, countdown: int, do: Callable, start: bool = True, loop: bool = True, first_check: bool = False):
        super(Timer, self).__init__()
        self.countdown: int = countdown
        self.current_time: int = 0
        self.last_update: int = -1
        self.running: bool = False
        self.do: Callable = do
        self.loop: bool = loop
        self.first_check: bool = first_check
        if start:
            self.start_timer()

    def start_timer(self) -> None:
        """
        Start the timer
        :return: None
        """
        self.running = True
        self.current_time = pygame.time.get_ticks()
        self.last_update = pygame.time.get_ticks()

    def stop_timer(self) -> None:
        """
        Stop the timer
        :return: None
        """
        self.running = False

    def update(self) -> None:
        """
        Checks whether the timer should call the function
        :return: None
        """
        if self.running:
            self.current_time = pygame.time.get_ticks()
            if self.current_time - self.last_update >= self.countdown or not self.first_check:
                self.first_check = True
                self.last_update = self.current_time
                self.do()

    def get_percentage(self) -> float:
        """
        Returns the percentage of timer completion
        :return: percentage of timer completion
        """
        return (self.current_time - self.last_update) / self.countdown
