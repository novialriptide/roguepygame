import collections.abc
from typing import Optional, Type, Any, Callable, TYPE_CHECKING, Protocol, Iterator, TypeVar, Generic, Union

import pygame
import constants as const
if TYPE_CHECKING:
    import game
    class SupportsEvents(Protocol):
        def events(self, event: pygame.event.Event) -> None: ...
_GAME_OBJECT_TYPE = TypeVar('_GAME_OBJECT_TYPE', bound='GameObject')


class Scene:
    """
    Class used to represent the game scene
    it is responsible for processing the events, updating the game state, and rendering the game
    """
    def __init__(self, object_manager, **kwargs):
        self.program: game.Game = const.program
        self.object_manager: ObjectManager = object_manager
        self.background: pygame.Surface = pygame.Surface(const.SCREEN_SIZE)
        self.state: dict[str, Any] = {
            'mouse_pos': (-1000, -1000)  # TODO Reconsider if we need this information
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
        self.object_manager.object_events(events)

    def update(self) -> None:
        """
        Method used to update the game.
        Gets called after Scene.events() every iteration of game loop.
        :return: None
        """
        self.object_manager.object_update()

    def render(self, screen: pygame.Surface) -> None:
        """
        Method used to render the game.
        Method gets the game window as the argument.
        Gets called after Scene.update() every iteration of game loop.
        :param screen: Game window
        :return: None
        """
        screen.blit(self.background, (0, 0))
        self.object_manager.object_render(screen)

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
        self.object_manager: ObjectManager = ObjectManager()
        self.scene: Optional[Scene] = None
        self.next_scene: Optional[tuple[Union[Scene, Type[Scene]], dict[str, Any], ObjectManager]] = None
        self.saved_scenes: dict[str, Scene] = {}

    def start_program(self, scene: Type[Scene], **kwargs) -> None:
        self.scene = scene(self.object_manager, **kwargs)
        self.scene.program = self.program
        self.scene.start()

    def go_to(self, scene: Type[Scene], **kwargs) -> None:
        """
        Method you should call when you want to go to another scene at the end of the frame
        :param scene: reference to the scene you want to go to
        :param kwargs: arguments you want to pass to the new scene
        :return: None
        """
        if self.next_scene is None:
            self.next_scene = (scene, kwargs, self.object_manager)

    def go_to_with_save(self, name: str, scene: Type[Scene], **kwargs) -> None:
        if self.next_scene is None:
            self.saved_scenes[name] = self.scene
            self.next_scene = (scene, kwargs, ObjectManager())

    def load_scene(self, name: str) -> None:
        if self.next_scene is None:
            scene = self.saved_scenes.pop(name)
            self.next_scene = (scene, None, scene.object_manager)

    def end_frame(self) -> None:
        if self.next_scene is not None:
            if isinstance(self.next_scene[0], type):
                if self.object_manager != self.next_scene[2]:
                    self.object_manager.save_objects()
                    self.object_manager = self.next_scene[2]
                else:
                    self.object_manager.clear_objects()
                    self.scene.end()
                self.scene = self.next_scene[0](self.object_manager, **self.next_scene[1])
                self.scene.program = self.program
                self.scene.start()
            else:
                self.object_manager = self.next_scene[2]
                self.scene = self.next_scene[0]
                self.object_manager.load_objects()
            self.next_scene = None


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
        self.groups: dict[str, ObjectGroup] = {}
        self.event_manager: EventManager = EventManager()

    def object_events(self, events: list[pygame.event.Event]) -> None:
        """
        Method used to call the events() method of all objects
        :param events: list of pygame events
        :return: None
        """
        self.event_manager.check_events(events)

    def object_update(self) -> None:
        """
        Method used to call the update() method of all objects
        :return: None
        """
        for obj in self.objects:
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

    def add_object(self, obj: "GameObject", group_name: Optional[str]=None) -> None:
        """
        Method used to add new object to the object manager
        :param obj: GameObject you want to add
        :param group_name: Name of the group you want the object to be in
        :return: None
        """
        self.objects.append(obj)
        self.objects.sort(key=layer_sort_key)
        if group_name is not None:
            self.add_object_to_group(obj, group_name)

    def remove_object(self, obj: "GameObject") -> None:
        """
        Method used to remove object from the list of objects
        :param obj: GameObject you want to remove
        :return: None
        """
        self.event_manager.remove_object(obj)
        self.objects.remove(obj)
        for object_group in self.groups.values():
            object_group.remove_object(obj)

    def add_object_to_group(self, obj: "GameObject", group_name: str) -> None:
        """
        Method used to add the object to the group
        :param obj: GameObject you want to add
        :param group_name: Name of the group you want the object to be in
        :return: None
        """
        if group_name not in self.groups:
            self.groups[group_name] = ObjectGroup()
        self.groups[group_name].add_object(obj)

    def get_group(self, group_name: str) -> "ObjectGroup":
        """
        Method that returns object group
        :param group_name: name of the group you want
        :return: ObjectGroup
        :raise ValueError: if group name doesn't exist
        """
        if group_name not in self.groups:
            raise ValueError(f"Group {group_name} doesn't exist")
        return self.groups[group_name]

    def get_objects_of_type(self, object_type: Type[_GAME_OBJECT_TYPE]) -> Iterator[_GAME_OBJECT_TYPE]:
        return GameObjectIterator(self, object_type)

    def clear_objects(self) -> None:
        """
        Method used to remove all objects from the list of objects
        :return: None
        """
        copy_of_objects = self.objects.copy()
        for obj in copy_of_objects:
            self.remove_object(obj)

    def save_objects(self) -> None:
        for obj in self.objects:
            obj.save_object()

    def load_objects(self) -> None:
        for obj in self.objects:
            obj.load_object()


class EventManager:
    """
    Class used to transport pygame Events to GameObjects
    """
    def __init__(self):
        self.program: game.Game = const.program
        self.listeners: dict[int, list[SupportsEvents]] = {}

    def subscribe(self, event_type: int, obj: "SupportsEvents") -> None:
        """
        Method that adds object for which the event manager should check events
        :param event_type: type of the event that should be checked for the object
        :param obj: object to check events for
        :return: None
        """
        if event_type in self.listeners:
            self.listeners[event_type].append(obj)
        else:
            self.listeners[event_type] = [obj]

    def unsubscribe(self, event_type: int, obj: "SupportsEvents") -> None:
        """
        Method that removes object for which the event manager should check events
        :param event_type: type of the event that should be checked for the object
        :param obj: object to remove event checking for
        :return: None
        """
        if event_type in self.listeners:
            if obj in self.listeners[event_type]:
                self.listeners[event_type].remove(obj)
            if not self.listeners[event_type]:
                del self.listeners[event_type]

    def remove_object(self, obj: "SupportsEvents") -> None:
        """
        Method that removes all event listeners for an object
        :param obj: object you wish to remove from event manager
        :return: None
        """
        for event_type in list(self.listeners):
            self.unsubscribe(event_type, obj)

    def check_events(self, events: list[pygame.event.Event]) -> None:
        """
        Method that checks if there have been any relevant event and notifies the objects
        :param events: list of pygame Events
        :return: None
        """
        for event in events:
            if event.type in self.listeners:
                for listener in self.listeners[event.type]:
                    listener.events(event)

    def raise_event(self, event: int, **kwargs) -> None:
        pygame.event.post(pygame.event.Event(event, **kwargs))
        self.program.get_scene().events(pygame.event.get(event))

class GameObject:
    """
    Class used to represent the basic game object
    """
    def __init__(self):
        self.program: game.Game = const.program
        self.object_manager = self.program.get_object_manager()
        self.name: Optional[str] = None
        self.child_objects: dict[str, GameObject] = {}
        self.parent: Optional[GameObject] = None

    def add_child(self, child_obj: "GameObject", child_name: Optional[str] = None) -> None:
        """
        Method that creates the child of the GameObject
        :param child_obj: child object
        :param child_name: name of the child
        :return: None
        """
        if child_name is None:
            child_name = len(self.child_objects)
            while str(child_name) in self.child_objects:
                child_name += 1
        self.child_objects[str(child_name)] = child_obj
        child_obj.parent = self

    def add_object(self, name: Optional[str] = None, group_name: Optional[str] = None) -> "GameObject":
        """
        Method that adds the object and its children to the ObjectManager
        :param name: name of the object
        :param group_name: name of the group you want the object to be part of
        :return: self
        """
        if name is not None:
            self.name = name
        self.object_manager.add_object(self, group_name)
        for child in self.child_objects.values():
            child.add_object()
        return self

    def destroy_object(self) -> None:
        """
        Method to remove the object from the ObjectManager
        :return: None
        """
        for child in self.child_objects.values():
            child.destroy_object()
        self.object_manager.remove_object(self)

    def update(self) -> None:
        """
        Method used to update the object every frame.
        :return: None
        """
        pass

    def save_object(self) -> None:
        pass

    def load_object(self) -> None:
        pass


class DrawableObject(GameObject):
    """
    Class used to represent the object that is drawn on the Scene
    Requires image and rect attributes
    """

    def __init__(self, image: pygame.Surface = None, rect: pygame.Rect = None, layer: int = 1):
        super().__init__()
        self.image = image
        self.rect = rect
        self.layer = layer

    def render(self, screen: pygame.Surface) -> None:
        """
        Method that draws the object to the game window.
        :param screen: game window
        :return: None
        """
        if self.image is not None and self.rect is not None:
            screen.blit(self.image, self.rect)


class ClickableObject(DrawableObject):
    """
    Drawable object that can be clicked
    Must implement click_function()
    """
    def __init__(self):
        super().__init__()
        self.program.get_event_manager().subscribe(pygame.MOUSEBUTTONDOWN, self)

    def events(self, event: pygame.event.Event) -> None:
        """
        Method that checks whether the object was clicked
        :param event: Relevant event
        :return: None
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                if event.button == 1:
                    self.click_function(event.pos)
                if event.button == 3:
                    self.click_function_right(event.pos)
            else:
                if event.button == 1:
                    self.clicked_outside(event.pos)
                if event.button == 3:
                    self.click_function_right(event.pos)

    def click_function(self, position: tuple[int, int]):
        """
        Function that gets called when the object is clicked with the left mouse button
        :return: None
        """
        raise NotImplementedError(f"{self.__class__.__name__} ClickableObject must implement click_function method!")

    def click_function_right(self, position: tuple[int, int]):
        """
        Function that gets called when the object is clicked with the right mouse button
        :return: None
        """
        pass

    def clicked_outside(self, position: tuple[int, int]):
        pass

    def clicked_outside_right(self, position: tuple[int, int]):
        pass


class Timer(GameObject):
    """
    Class used for timer
    """
    def __init__(self, countdown: int, do: Callable, start: bool = True, loop: bool = True, first_check: bool = False):
        super().__init__()
        self.countdown: int = countdown
        self.current_time: int = 0
        self.last_update: int = -1
        self.time_difference: int = 0
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

    def restart_timer(self):
        self.first_check = False

    def save_object(self) -> None:
        self.time_difference = pygame.time.get_ticks() - self.last_update
        self.running = not self.running

    def load_object(self) -> None:
        self.current_time = pygame.time.get_ticks()
        self.last_update = self.current_time - self.time_difference
        self.time_difference = 0
        self.running = not self.running

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


class ObjectGroup:
    """
    Class used to represent the group of objects
    """
    def __init__(self):
        self.objects: list[GameObject] = []

    def __iter__(self) -> Iterator[GameObject]:
        return self.objects.__iter__()

    def add_object(self, obj: GameObject) -> None:
        """
        Method used to add an object to the group
        :param obj: object to add
        :return: None
        """
        self.objects.append(obj)

    def remove_object(self, obj: GameObject) -> None:
        """
        Method used to remove the object from the group
        :param obj: object to remove
        :return: None
        """
        if obj in self.objects:
            self.objects.remove(obj)

    def group_collide(self, obj: DrawableObject) -> list[DrawableObject]:
        """
        Method used to return the list of object from the group that obj collides with
        :param obj: object to check the collision for
        :return: list of objects colliding with obj
        """
        colliding_objects = []
        for group_object in self.objects:
            if isinstance(group_object, DrawableObject):
                if obj.rect.colliderect(group_object.rect):
                    colliding_objects.append(group_object)
        return colliding_objects


# Helper stuff
class GameObjectIterator(collections.abc.Iterator, Generic[_GAME_OBJECT_TYPE]):
    """
    Creates iterator that goes over specific objects in ObjectManager
    """
    def __init__(self, object_manager: ObjectManager, object_type: Type[_GAME_OBJECT_TYPE]):
        self.idx = 0
        self.object_manager = object_manager
        self.object_type = object_type
        self.number_of_objects = len(self.object_manager.objects)

    def __next__(self) -> _GAME_OBJECT_TYPE:
        for i in range(self.idx, self.number_of_objects):
            obj = self.object_manager.objects[i]
            if isinstance(obj, self.object_type):
                self.idx = i + 1
                return obj
        else:
            raise StopIteration  # Done iterating.

def layer_sort_key(x: GameObject) -> int:
    """
    Function used to return layer for sorting
    :param x: GameObject
    :return: layer of the GameObject
    """
    return x.layer if hasattr(x, 'layer') else 0