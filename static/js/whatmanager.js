'use strict';

angular.
    module('whatManagerApp', []).
    factory('whatManagerService', function($q, $http, $timeout) {
        var service = {};
        var subscriptions = {};

        function makeSubscription(propName, endpoint) {
            var timeoutHandle = null;
            var httpCanceller = null;
            var performUpdate = function() {
                timeoutHandle = null;
                httpCanceller = $q.defer();
                $http.get('/api/' + endpoint, {
                    timeout: httpCanceller.promise
                }).success(function(resp) {
                    $.each(subscriptions[endpoint].scopes, function(i, scope) {
                        scope[propName] = resp;
                    });
                    timeoutHandle = $timeout(performUpdate, 3000, false);
                    httpCanceller = null;
                }).error(function() {
                    timeoutHandle = $timeout(performUpdate, 3000, false);
                    httpCanceller = null;
                });
            };
            var forceUpdate = function() {
                if (timeoutHandle !== null) {
                    $timeout.cancel(timeoutHandle);
                }
                if (httpCanceller !== null) {
                    httpCanceller.resolve();
                }
                performUpdate();
            };
            var cancel = function() {
                if (timeoutHandle === null) {
                    $timeout.cancel(timeoutHandle);
                }
                if (httpCanceller === null) {
                    httpCanceller.resolve();
                }
            };
            performUpdate();
            return {
                forceUpdate: forceUpdate,
                cancel: cancel
            }
        }

        service.subscribeScope = function(scope, propName, endpoint) {
            if (subscriptions[endpoint] == undefined) {
                subscriptions[endpoint] = {
                    scopes: [],
                    obj: makeSubscription(propName, endpoint)
                };
            }
            var subscription = subscriptions[endpoint];
            var scopeIndex = subscription.scopes.indexOf(scope);
            if (scopeIndex !== -1) {
                return subscription.obj;
            }
            subscription.scopes.push(scope);
            scope.$on('$destroy', function() {
                var scopeIndex = subscription.scopes.indexOf(scope);
                subscription.scopes.splice(scopeIndex, 1);
                if (subscription.scopes.length === 0) {
                    subscription.obj.cancel();
                    delete subscriptions[endpoint];
                }
            });
        };
        return service
    }).
    directive('diskSpaceChart', function($filter) {
        function labelFormatter(label, series) {
            var bytes = $filter('fileSizeFormat')(series.data[0][1]);
            return "<div style='font-size:8pt; text-align:center; padding:2px; color:white;'>" +
                label + "<br/>" + bytes + ' (' + Math.round(series.percent) + "%)</div>";
        }

        return {
            restrict: 'EA',
            link: function(scope, elem, attrs) {
                var location = scope[attrs.ngModel];
                var data = [
                    { label: 'Used Space', data: location.used },
                    { label: 'Free Space', data: location.free }
                ];
                $.plot(elem, data, {
                    series: {
                        pie: {
                            show: true,
                            radius: 1,
                            label: {
                                show: true,
                                radius: 0.50,
                                formatter: labelFormatter
                            }
                        }
                    },
                    legend: {
                        show: false
                    },
                    colors: ['#444', '#999']
                });
                elem.show();
            }
        };
    }).
    filter('fileSizeFormat', function() {
        var suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB'];
        return function(value) {
            if (value === undefined || value === null) {
                return '';
            }
            var result = null;
            $.each(suffixes, function(i, suffix) {
                if (value < 10) {
                    result = (Math.floor(value * 100) / 100) + ' ' + suffix;
                } else if (value < 100) {
                    result = (Math.floor(value * 10) / 10) + ' ' + suffix;
                } else if (value < 1024) {
                    result = Math.floor(value) + ' ' + suffix;
                } else {
                    value /= 1024;
                    return true;
                }
                return false;
            });
            if (result == null) {
                result = Math.floor(value * 1024) + ' ' + suffixes[suffixes.length - 1];
            }
            return result;
        }
    }).
    filter('slice', function() {
        return function(arr, start, end) {
            if (arr === undefined) {
                return undefined;
            }
            return arr.slice(start, end);
        };
    }).
    controller('SiteStatisticsController', function($scope, whatManagerService) {
        var subscription = whatManagerService.subscribeScope($scope, 'stats', 'stats');
        $scope.forceUpdate = function() {
            subscription.forceUpdate();
        }
    })
;
