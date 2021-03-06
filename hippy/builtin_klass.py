""" This module implements helpers for implementing builtin classes.
"""
from hippy.klass import GetterSetter, def_class
from hippy.builtin import wrap_method, Optional, W_Root, ThisUnwrapper
from hippy.objects.instanceobject import W_InstanceObject
from hippy import consts


class GetterSetterWrapper(object):
    def __init__(self, getter, setter, name, accflags):
        self.getter = getter
        self.setter = setter
        self.name = name
        self.accflags = accflags

    def build(self, klass):
        return GetterSetter(self.getter, self.setter, self.name, klass,
                            self.accflags)


class W_ExceptionObject(W_InstanceObject):
    def setup(self, interp):
        self.traceback = interp.get_traceback()

    def get_message(self, interp):
        return self.getattr(interp, 'message', k_Exception)


@wrap_method(['interp', ThisUnwrapper(W_ExceptionObject),
              Optional(str), Optional(int), Optional('object')],
             name='Exception::__construct')
def new_exception(interp, this, message='', code=0, w_previous=None):
    this.setattr(interp, 'file', interp.space.wrap(this.traceback[0][0]), k_Exception)
    this.setattr(interp, 'message', interp.space.wrap(message), k_Exception)
    this.setattr(interp, 'code', interp.space.wrap(code), k_Exception)
    if w_previous is None:
        w_previous = interp.space.w_Null
    elif not k_Exception.is_parent_of(w_previous.klass):
        interp.fatal("Wrong parameters for "
                     "Exception([string $exception [, long $code [, "
                     "Exception $previous = NULL]]])")
    this.setattr(interp, 'previous', w_previous, k_Exception)


@wrap_method(['interp', 'this'], name='Exception::getMessage')
def exc_getMessage(interp, this):
    return this.getattr(interp, 'message', k_Exception)


@wrap_method(['interp', 'this'], name='Exception::getCode')
def exc_getCode(interp, this):
    return this.getattr(interp, 'code', k_Exception)


@wrap_method(['interp', 'this'], name='Exception::getPrevious')
def exc_getPrevious(interp, this):
    return this.getattr(interp, 'previous', k_Exception)


@wrap_method(['interp', ThisUnwrapper(W_ExceptionObject)],
             name='Exception::getTrace')
def exc_getTrace(interp, this):
    from hippy.module.internal import backtrace_to_applevel
    return backtrace_to_applevel(interp.space, this.traceback)

@wrap_method(['interp', ThisUnwrapper(W_ExceptionObject)],
             name='Exception::getFile')
def exc_getFile(interp, this):
    return this.getattr(interp, 'file', k_Exception)

@wrap_method(['interp', ThisUnwrapper(W_ExceptionObject)],
             name='Exception::getLine')
def exc_getLine(interp, this):
    return this.getattr(interp, 'line', k_Exception)

@wrap_method(['interp', ThisUnwrapper(W_ExceptionObject)],
             name='Exception::__toString')
def exc___toString(interp, this):
    name = this.klass.name
    space = interp.space
    message = space.str_w(this.getattr(interp, 'message', k_Exception))
    file = space.str_w(this.getattr(interp, 'file', k_Exception))
    line = space.int_w(this.getattr(interp, 'line', k_Exception))
    msg = ["exception '%s' with message '%s' in %s:%d" % (name, message, file, line)]
    msg.append("Stack trace")
    for i, (filename, funcname, line, source) in enumerate(this.traceback):
        msg.append("#%d %s(%d): %s()" % (i, filename, line, funcname))
    return space.wrap("\n".join(msg))

@wrap_method(['interp', ThisUnwrapper(W_ExceptionObject)],
             name='Exception::getTraceAsString')
def exc_getTraceAsString(interp, this):
    msg = []
    for i, (filename, funcname, line, source) in enumerate(this.traceback):
        msg.append("#%d %s(%d): %s()" % (i, filename, line, funcname))
    return interp.space.wrap("\n".join(msg))


k_Exception = def_class('Exception',
    [new_exception, exc_getMessage, exc_getCode, exc_getPrevious,
     exc_getTrace, exc_getFile, exc_getLine, exc___toString,
     exc_getTraceAsString],
          [('message', consts.ACC_PROTECTED),
           ('code', consts.ACC_PROTECTED),
           ('previous', consts.ACC_PRIVATE),
           ('file', consts.ACC_PROTECTED),
           ('line', consts.ACC_PROTECTED),
           ],
          instance_class=W_ExceptionObject)

def_class('OutOfBoundsException', [], extends=k_Exception, instance_class=W_ExceptionObject)
k_stdClass = def_class('stdClass', [])
k_incomplete = def_class('__PHP_Incomplete_Class', [])
k_RuntimeException = def_class('RuntimeException', [], extends=k_Exception, instance_class=W_ExceptionObject)
k_LogicException = def_class('LogicException', [], extends=k_Exception, instance_class=W_ExceptionObject)
k_DomainException = def_class('DomainException', [], extends=k_Exception, instance_class=W_ExceptionObject)


class W_ReflectionObject(W_InstanceObject):
    refl_klass = None

    def get_refl_klass(self, interp):
        if self.refl_klass is None:
            interp.fatal("Internal error: Failed to retrieve the "
                         "reflection object")
        return self.refl_klass


@wrap_method(['interp', ThisUnwrapper(W_ReflectionObject), str],
             name='ReflectionClass::__construct')
def construct_ReflectionClass(interp, this, name):
    space = interp.space
    this.setattr(interp, 'name', space.wrap(name), None)
    this.refl_klass = interp.lookup_class_or_intf(name)


@wrap_method(['interp', ThisUnwrapper(W_ReflectionObject), 'args_w'],
             name='ReflectionClass::newInstance')
def newInstance(interp, this, args_w):
    return this.get_refl_klass(interp).call_args(interp, args_w)


@wrap_method(['interp', ThisUnwrapper(W_ReflectionObject), W_Root],
             name='ReflectionClass::newInstanceArgs')
def newInstanceArgs(interp, this, w_arr):
    args_w = interp.space.as_array(w_arr).as_list_w()
    return this.get_refl_klass(interp).call_args(interp, args_w)

def_class('ReflectionClass',
    [construct_ReflectionClass,
     newInstance, newInstanceArgs],
    instance_class=W_ReflectionObject
)


def new_abstract_method(args, **kwds):
    name = kwds['name']
    assert args[0] == 'interp'
    kwds['flags'] = kwds.get('flags', 0) | consts.ACC_ABSTRACT

    def method(interp, *args):
        interp.fatal("Cannot call abstract method %s()" % (name,))
    return wrap_method(args, **kwds)(method)


k_Iterator = def_class('Iterator',
    [new_abstract_method(["interp"], name="Iterator::current"),
     new_abstract_method(["interp"], name="Iterator::next"),
     new_abstract_method(["interp"], name="Iterator::key"),
     new_abstract_method(["interp"], name="Iterator::rewind"),
     new_abstract_method(["interp"], name="Iterator::valid")],
    flags=consts.ACC_INTERFACE | consts.ACC_ABSTRACT,
    is_iterator=True
)


def_class('SeekableIterator',
    [new_abstract_method(["interp"], name="SeekableIterator::seek")],
    flags=consts.ACC_INTERFACE | consts.ACC_ABSTRACT, implements=[k_Iterator])


def_class('RecursiveIterator',
    [new_abstract_method(["interp"], name="RecursiveIterator::hasChildren"),
     new_abstract_method(["interp"], name="RecursiveIterator::getChildren")],
    flags=consts.ACC_INTERFACE | consts.ACC_ABSTRACT, implements=[k_Iterator])


def_class('Countable',
    [new_abstract_method(["interp"], name="Countable::count")],
    flags=consts.ACC_INTERFACE | consts.ACC_ABSTRACT
)
