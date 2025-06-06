(function () {
  'use strict';

  angular
    .module('horizon.app.core.images')
    .factory('horizon.app.core.images.actions.deactivate-image.service', deactivateImageService);

  deactivateImageService.$inject = [
    '$q',
    'horizon.app.core.openstack-service-api.glance',
    'horizon.app.core.openstack-service-api.policy',
    'horizon.framework.util.actions.action-result.service',
    'horizon.framework.util.i18n.gettext',
    'horizon.framework.util.q.extensions',
    'horizon.framework.widgets.modal.simple-modal.service',
    'horizon.framework.widgets.toast.service',
    'horizon.app.core.images.resourceType'
  ];

  /*
   * @ngdoc factory
   * @name horizon.app.core.images.actions.deactivate-image.service
   *
   * @Description
   * Brings up the deactivate image confirmation modal dialog.

   * On submit, deactivate the given image
   * On cancel, do nothing.
   */
  function deactivateImageService(
    $q,
    glance,
    policy,
    actionResultService,
    gettext,
    $qExtensions,
    simpleModal,
    toast,
    imagesResourceType
  ) {
    var notAllowedMessage = gettext("You are not allowed to deactivate image: %s");

    var service = {
      allowed: allowed,
      perform: perform
    };

    return service;

    //////////////

    function perform(image) {
      var context = {};
      context.labels = labelize();
      context.deactivateEntity = deactivateImage;

      return $qExtensions.allSettled([checkPermission(image)]).then(afterCheck);

      function checkPermission(image) {
        return { promise: allowed(image), context: image };
      }

      function afterCheck(result) {
        var outcome = $q.reject().catch(angular.noop);  // Reject the promise by default
        if (result.fail.length > 0) {
          toast.add('error', getMessage(notAllowedMessage, result.fail));
          outcome = $q.reject(result.fail).catch(angular.noop);
        }
        if (result.pass.length > 0) {
          var modalParams = {
            title: context.labels.title,
            body: interpolate(context.labels.message, [result.pass.map(getEntity)[0].name]),
            submit: context.labels.submit
          };
          outcome = simpleModal.modal(modalParams).result
          .then(function () {
            return deactivateImage(image);
          })
          .then(
            function() { return onDeactivateImageSuccess(image); }
          );
        }
        return outcome;
      }
    }

    function allowed(image) {
      return $q.all([
        policy.ifAllowed({ rules: [['image', 'deactivate']] }),
        notDeactivated(image),
        notProtected(image)
      ]);
    }

    function onDeactivateImageSuccess(image) {
      toast.add('success', interpolate(labelize().success, [image.name]));
      return actionResultService.getActionResult()
        .updated(imagesResourceType, image.id)
        .result;
    }

    function labelize() {
      return {
        title: gettext('Confirm Deactivate Image'),
        message: gettext('You have selected "%s". A deactivated image is not downloadable.'),
        submit: gettext('Deactivate Image'),
        success: gettext('Deactivated Image: %s.'),
        error: gettext('Unable to deactivate Image: %s.')
      };
    }

    function notDeactivated(image) {
      return $qExtensions.booleanAsPromise(image.status !== 'deactivated');
    }

    function notProtected(image) {
      return $qExtensions.booleanAsPromise(!image.protected);
    }

    function deactivateImage(image) {
      return glance.deactivateImage(image);
    }

    function getMessage(message, image) {
      return interpolate(message, [image.name]);
    }

    function getEntity(result) {
      return result.context;
    }
  }
})();
