"""
Test cases for Call Stack Manager
"""
from mock import patch
from django.db import models
from django.test import TestCase
from openedx.core.djangoapps.call_stack_manager import donottrack
from openedx.core.djangoapps.call_stack_manager import CallStackManager, CallStackMixin


class ModelMixinCSM(CallStackMixin, models.Model):
    """
    Test Model class which uses both CallStackManager, and CallStackMixin
    """
    # override Manager objects
    objects = CallStackManager()
    id_field = models.IntegerField()


class ModelMixin(CallStackMixin, models.Model):
    """
    Test Model that uses CallStackMixin but does not use CallStackManager
    """
    id_field = models.IntegerField()


class ModelNothing(models.Model):
    """
    Test Model class that neither uses CallStackMixin nor CallStackManager
    """
    id_field = models.IntegerField()


class ModelAnotherCSM(models.Model):
    """
    Test Model class that only uses overridden Manager CallStackManager
    """
    objects = CallStackManager()
    id_field = models.IntegerField()


class ModelWithCSM(models.Model):
    """
    Test Model Class with overridden CallStackManager
    """
    objects = CallStackManager()
    id_field = models.IntegerField()


class ModelWithCSMChild(ModelWithCSM):
    """child class of ModelWithCSM
    """
    objects = CallStackManager()
    child_id_field = models.IntegerField()


@donottrack(ModelWithCSM)
def donottrack_subclass():
    """ function in which subclass and superclass calls QuerySetAPI
    """
    ModelWithCSM.objects.filter(id_field=1)
    ModelWithCSMChild.objects.filter(child_id_field=1)


def track_without_donottrack():
    """ function calling QuerySetAPI, another function, again QuerySetAPI
    """
    ModelAnotherCSM.objects.filter(id_field=1)
    donottrack_child_func()
    ModelAnotherCSM.objects.filter(id_field=1)


@donottrack(ModelAnotherCSM)
def donottrack_child_func():
    """ decorated child function
    """
    # should not be tracked
    ModelAnotherCSM.objects.filter(id_field=1)

    # should be tracked
    ModelMixinCSM.objects.filter(id_field=1)


@donottrack(ModelMixinCSM)
def donottrack_parent_func():
    """ decorated parent function
    """
    # should not  be tracked
    ModelMixinCSM.objects.filter(id_field=1)
    # should be tracked
    ModelAnotherCSM.objects.filter(id_field=1)
    donottrack_child_func()


@donottrack()
def donottrack_func_parent():
    """ non-parameterized @donottrack decorated function calling child function
    """
    ModelMixin.objects.all()
    donottrack_func_child()
    ModelMixin.objects.filter(id_field=1)


@donottrack()
def donottrack_func_child():
    """ child decorated non-parameterized function
    """
    # Should not be tracked
    ModelMixin.objects.all()


class TestingCallStackManager(TestCase):
    """Tests for call_stack_manager
    1. Tests CallStackManager QuerySetAPI functionality
    2. Tests @donottrack decorator
    """
    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_save(self, log_capt):
        """ tests save() of CallStackMixin/ applies same for delete()
        classes with CallStackMixin should participate in logging.
        """
        ModelMixin(id_field=1).save()
        self.assertEqual(ModelMixin, log_capt.call_args[0][1])

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_withoutmixin_save(self, log_capt):
        """tests save() of CallStackMixin/ applies same for delete()
        classes without CallStackMixin should not participate in logging
        """
        ModelAnotherCSM(id_field=1).save()
        self.assertEqual(len(log_capt.call_args_list), 0)

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_queryset(self, log_capt):
        """ Tests for Overriding QuerySet API
        classes with CallStackManager should get logged.
        """
        ModelMixinCSM(id_field=1).save()
        ModelMixinCSM.objects.all()
        self.assertEqual(ModelMixinCSM, log_capt.call_args[0][1])

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_withoutqueryset(self, log_capt):
        """ Tests for Overriding QuerySet API
        classes without CallStackManager should not get logged
        """
        # create and save objects of class not overriding queryset API
        ModelNothing(id_field=1).save()
        # class not using Manager, should not get logged
        ModelNothing.objects.all()
        self.assertEqual(len(log_capt.call_args_list), 0)

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_donottrack(self, log_capt):
        """ Test for @donottrack
        calls in decorated function should not get logged
        """
        donottrack_func_parent()
        self.assertEqual(len(log_capt.call_args_list), 0)

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_parameterized_donottrack(self, log_capt):
        """ Test for parameterized @donottrack
        classes specified in the decorator @donottrack should not get logged
        """
        donottrack_child_func()
        self.assertEqual(ModelMixinCSM, log_capt.call_args[0][1])

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_nested_parameterized_donottrack(self, log_capt):
        """ Tests parameterized nested @donottrack
        should not track call of classes specified in decorated with scope bounded to the respective class
        """
        ModelAnotherCSM(id_field=1).save()
        donottrack_parent_func()
        self.assertEqual(ModelAnotherCSM, log_capt.call_args_list[0][0][1])
        self.assertEqual(ModelMixinCSM, log_capt.call_args_list[1][0][1])

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_nested_parameterized_donottrack_after(self, log_capt):
        """ Tests parameterized nested @donottrack
        QuerySetAPI calls after calling function with @donottrack should get logged
        """
        donottrack_child_func()
        # class with CallStackManager as Manager
        ModelAnotherCSM(id_field=1).save()
        # test is this- that this should get called.
        ModelAnotherCSM.objects.filter(id_field=1)
        self.assertEqual(ModelMixinCSM, log_capt.call_args_list[0][0][1])
        self.assertEqual(ModelAnotherCSM, log_capt.call_args_list[1][0][1])

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_donottrack_called_in_func(self, log_capt):
        """ test for function which calls decorated function
        functions without @donottrack decorator should log
        """
        ModelAnotherCSM(id_field=1).save()
        ModelMixinCSM(id_field=1).save()
        track_without_donottrack()
        self.assertEqual(ModelMixinCSM, log_capt.call_args_list[0][0][1])
        self.assertEqual(ModelAnotherCSM, log_capt.call_args_list[1][0][1])
        self.assertEqual(ModelMixinCSM, log_capt.call_args_list[2][0][1])
        self.assertEqual(ModelAnotherCSM, log_capt.call_args_list[3][0][1])

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_donottrack_child_too(self, log_capt):
        """ Test for inheritance
        subclass should not be tracked when superclass is called in a @donottrack decorated function
        """
        ModelWithCSM(id_field=1).save()
        ModelWithCSMChild(id_field=1, child_id_field=1).save()
        donottrack_subclass()
        self.assertEqual(len(log_capt.call_args_list), 0)

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_duplication(self, log_capt):
        """ Test for duplication of call stacks
        should not log duplicated call stacks
        """
        for __ in range(1, 5):
            ModelMixinCSM(id_field=1).save()
        self.assertEqual(len(log_capt.call_args_list), 1)
