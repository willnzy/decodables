"""
Experiment Service - Domain service for A/B testing experiments.

@module domains.platform.experiments.service
@version 1.0.0

This is the DDD-compliant service that uses ExperimentRepository.
Replaces the module-function approach in crud.py with class-based service.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple

from infrastructure.repositories.experiment_repository import SupabaseExperimentRepository

logger = logging.getLogger(__name__)


class ExperimentService:
    """
    Domain service for experiment management.

    Responsibilities:
    - Experiment CRUD operations
    - Experiment lifecycle management (status updates)
    - Active experiment queries
    """

    def __init__(self, experiment_repo: SupabaseExperimentRepository):
        """
        Initialize service with repository.

        Args:
            experiment_repo: Experiment repository instance
        """
        self._repo = experiment_repo

    async def list_experiments(
        self,
        status: Optional[str] = None,
        experiment_type: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict], int]:
        """
        List experiments with filters.

        Args:
            status: Filter by experiment status
            experiment_type: Filter by experiment type
            offset: Number of items to skip (DDD standard pagination)
            limit: Maximum number of items to return

        Returns:
            Tuple of (experiments list, total count)
        """
        try:
            experiments, total = await self._repo.list_experiments(
                status=status,
                experiment_type=experiment_type,
                offset=offset,
                limit=limit
            )
            return (experiments, total)
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to list: {e}")
            return ([], 0)

    async def get_experiment(self, experiment_key: str) -> Optional[Dict]:
        """
        Get experiment by key.

        Args:
            experiment_key: Experiment identifier

        Returns:
            Experiment dict or None
        """
        try:
            experiment = await self._repo.get_by_key(experiment_key)
            return experiment
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to get {experiment_key}: {e}")
            return None

    async def get_experiment_by_id(self, experiment_id: str) -> Optional[Dict]:
        """
        Get experiment by ID.

        Args:
            experiment_id: Experiment UUID

        Returns:
            Experiment dict or None
        """
        try:
            result = await self._repo.get_by_id(experiment_id)
            if result:
                # Convert Experiment aggregate to dict
                return result.__dict__ if hasattr(result, '__dict__') else result
            return None
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to get by ID {experiment_id}: {e}")
            return None

    async def get_active_experiments(self) -> List[Dict]:
        """
        Get all active (running) experiments.

        Returns:
            List of active experiments
        """
        try:
            experiments, _ = await self._repo.list_experiments(
                status="running",
                offset=0,
                limit=10000  # Get all active experiments
            )
            return experiments
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to get active experiments: {e}")
            return []

    async def create_experiment(
        self,
        experiment_key: str,
        name: str,
        description: str,
        experiment_type: str,
        variants: List[Dict],
        targeting: Optional[Dict] = None,
        metrics: Optional[List[Dict]] = None,
        status: str = "draft"
    ) -> Optional[Dict]:
        """
        Create new experiment.

        Args:
            experiment_key: Unique experiment identifier
            name: Human-readable name
            description: Experiment description
            experiment_type: Type (ab, multivariate, feature_flag)
            variants: List of variant configurations
            targeting: Targeting rules
            metrics: List of metrics to track
            status: Initial status (default: draft)

        Returns:
            Created experiment dict or None
        """
        try:
            # Build experiment data
            experiment_data = {
                "experiment_key": experiment_key,
                "name": name,
                "description": description,
                "experiment_type": experiment_type,
                "variants": variants,
                "targeting": targeting,
                "metrics": metrics,
                "status": status
            }

            result = await self._repo.create(experiment_data)
            return result
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to create {experiment_key}: {e}")
            return None

    async def update_experiment(
        self,
        experiment_key: str,
        **kwargs
    ) -> Optional[Dict]:
        """
        Update experiment.

        Args:
            experiment_key: Experiment identifier
            **kwargs: Fields to update

        Returns:
            Updated experiment dict or None
        """
        try:
            result = await self._repo.update(experiment_key, kwargs)
            return result
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to update {experiment_key}: {e}")
            return None

    async def update_experiment_status(
        self,
        experiment_key: str,
        status: str
    ) -> Optional[Dict]:
        """
        Update experiment status.

        Args:
            experiment_key: Experiment identifier
            status: New status (draft, running, paused, completed)

        Returns:
            Updated experiment dict or None
        """
        try:
            result = await self._repo.update_status(experiment_key, status)
            return result
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to update status {experiment_key}: {e}")
            return None

    async def delete_experiment(self, experiment_key: str) -> bool:
        """
        Delete experiment.

        Args:
            experiment_key: Experiment identifier

        Returns:
            True if deleted successfully
        """
        try:
            result = await self._repo.delete(experiment_key)
            return result
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to delete {experiment_key}: {e}")
            return False

    # ==========================================
    # Analysis Methods
    # ==========================================

    async def aggregate_experiment_results(self, experiment_key: Optional[str] = None) -> bool:
        """
        Aggregate results for experiment(s).

        Args:
            experiment_key: Specific experiment, or None for all running experiments

        Returns:
            Success status
        """
        try:
            if experiment_key:
                experiment = await self.get_experiment(experiment_key)
                if not experiment:
                    logger.error(f"[ExperimentService] Experiment not found: {experiment_key}")
                    return False
                experiments = [experiment]
            else:
                # Aggregate all running experiments
                experiments, _ = await self.list_experiments(status="running", limit=10000)

            for exp in experiments:
                if not exp:
                    continue
                await self._aggregate_single_experiment(exp)

            return True

        except Exception as e:
            logger.error(f"[ExperimentService] Aggregation failed: {e}")
            return False

    async def get_experiment_results(
        self,
        experiment_key: str,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None
    ) -> Optional[Dict]:
        """
        Get experiment results.

        Args:
            experiment_key: Experiment identifier
            start_date: Optional start date filter (not yet implemented)
            end_date: Optional end date filter (not yet implemented)

        Returns:
            Results dictionary with experiment info, results data, and aggregated_at timestamp
        """
        try:
            experiment = await self.get_experiment(experiment_key)
            if not experiment:
                return None

            # Get cached results from experiment_results table
            result = await self._repo._execute_query(
                lambda: self._repo.client.table("experiment_results").select("*")
                .eq("experiment_key", experiment_key)
            )

            if result and result.data:
                return {
                    "experiment": experiment,
                    "results": result.data[0].get("results", {}),
                    "aggregated_at": result.data[0].get("aggregated_at")
                }

            # No cached results, aggregate now
            await self._aggregate_single_experiment(experiment)

            # Fetch again
            result = await self._repo._execute_query(
                lambda: self._repo.client.table("experiment_results").select("*")
                .eq("experiment_key", experiment_key)
            )

            if result and result.data:
                return {
                    "experiment": experiment,
                    "results": result.data[0].get("results", {}),
                    "aggregated_at": result.data[0].get("aggregated_at")
                }

            return {"experiment": experiment, "results": {}}

        except Exception as e:
            logger.error(f"[ExperimentService] Failed to get results for {experiment_key}: {e}")
            return None

    async def _aggregate_single_experiment(self, experiment: Dict):
        """Aggregate results for a single experiment using SQL aggregation."""
        from datetime import datetime, timezone
        from collections import defaultdict

        exp_key = experiment.get('experiment_key')
        exp_id = experiment.get('id')

        try:
            # Get exposure counts by variant
            exposure_counts = await self._get_exposure_counts(exp_key)

            # Get conversion aggregates by variant and metric
            conversion_data = await self._get_conversion_aggregates(exp_key)

            # Build results
            results = {}
            for variant in experiment.get('variants', []):
                vk = variant.get('key')
                exp_count = exposure_counts.get(vk, 0)

                variant_result = {
                    "exposures": exp_count,
                    "metrics": {}
                }

                for mk, data in conversion_data.get(vk, {}).items():
                    conv_count = data["count"]
                    rate = conv_count / exp_count if exp_count > 0 else 0

                    variant_result["metrics"][mk] = {
                        "conversions": conv_count,
                        "rate": round(rate, 4),
                        "total_value": data["total"]
                    }

                results[vk] = variant_result

            # Store aggregated results
            await self._repo._execute_query(
                lambda: self._repo.client.table("experiment_results").upsert({
                    "experiment_id": exp_id,
                    "experiment_key": exp_key,
                    "results": results,
                    "aggregated_at": datetime.now(timezone.utc).isoformat()
                }, on_conflict="experiment_key")
            )

        except Exception as e:
            logger.error(f"[ExperimentService] Failed to aggregate {exp_key}: {e}")

    async def _get_exposure_counts(self, experiment_key: str) -> Dict[str, int]:
        """
        Get exposure counts by variant using SQL GROUP BY.
        Falls back to client-side aggregation if RPC not available.
        """
        from collections import defaultdict

        try:
            # Try using Supabase RPC for server-side aggregation
            result = await self._repo._execute_query(
                lambda: self._repo.client.rpc(
                    "aggregate_experiment_exposures",
                    {"exp_key": experiment_key}
                )
            )

            if result and result.data:
                return {row["variant_key"]: row["count"] for row in result.data}
        except Exception as e:
            logger.debug(f"[ExperimentService] RPC not available, using fallback: {e}")

        # Fallback: Use paginated fetch with limit
        exposure_counts = defaultdict(int)
        offset = 0
        batch_size = 1000

        while True:
            result = await self._repo._execute_query(
                lambda: self._repo.client.table("experiment_exposures")
                .select("variant_key")
                .eq("experiment_key", experiment_key)
                .range(offset, offset + batch_size - 1)
            )

            if not result or not result.data:
                break

            for row in result.data:
                exposure_counts[row.get("variant_key")] += 1

            if len(result.data) < batch_size:
                break

            offset += batch_size

        return dict(exposure_counts)

    async def _get_conversion_aggregates(self, experiment_key: str) -> Dict[str, Dict[str, Dict]]:
        """
        Get conversion aggregates by variant and metric using SQL GROUP BY.
        Falls back to client-side aggregation if RPC not available.
        """
        from collections import defaultdict

        try:
            # Try using Supabase RPC for server-side aggregation
            result = await self._repo._execute_query(
                lambda: self._repo.client.rpc(
                    "aggregate_experiment_conversions",
                    {"exp_key": experiment_key}
                )
            )

            if result and result.data:
                conversion_data = defaultdict(lambda: defaultdict(lambda: {"count": 0, "total": 0}))
                for row in result.data:
                    vk = row["variant_key"]
                    mk = row["metric_key"]
                    conversion_data[vk][mk]["count"] = row["count"]
                    conversion_data[vk][mk]["total"] = row["total_value"] or 0
                return dict(conversion_data)
        except Exception as e:
            logger.debug(f"[ExperimentService] RPC not available, using fallback: {e}")

        # Fallback: Use paginated fetch
        conversion_data = defaultdict(lambda: defaultdict(lambda: {"count": 0, "total": 0}))
        offset = 0
        batch_size = 1000

        while True:
            result = await self._repo._execute_query(
                lambda: self._repo.client.table("experiment_conversions")
                .select("variant_key, metric_key, value")
                .eq("experiment_key", experiment_key)
                .range(offset, offset + batch_size - 1)
            )

            if not result or not result.data:
                break

            for row in result.data:
                vk = row.get("variant_key")
                mk = row.get("metric_key")
                conversion_data[vk][mk]["count"] += 1
                conversion_data[vk][mk]["total"] += row.get("value", 0)

            if len(result.data) < batch_size:
                break

            offset += batch_size

        return dict(conversion_data)

    # ==========================================
    # Trend Methods
    # ==========================================

    async def get_daily_trend(self, experiment_key: str, days: int = 30) -> Optional[Dict]:
        """
        Get daily trend data for an experiment.

        Args:
            experiment_key: Experiment key
            days: Number of days to fetch (default 30)

        Returns:
            Trend data dict or None if experiment not found
        """
        from datetime import datetime, timedelta, timezone
        import json

        try:
            # Get experiment
            exp_result = await self._repo._execute_query(
                lambda: self._repo.client.table("experiments").select("id, variants")
                .eq("experiment_key", experiment_key)
            )

            if not exp_result or not exp_result.data:
                return None

            experiment = exp_result.data[0]
            experiment_id = experiment.get("id")
            variants = experiment.get("variants", [])

            # Parse variants
            if isinstance(variants, str):
                variants = json.loads(variants)

            variant_keys = [v.get("key") for v in variants]

            # Calculate start date
            now = datetime.now(timezone.utc)
            start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")

            # Query results with limit
            results_data = await self._repo._execute_query(
                lambda: self._repo.client.table("experiment_results").select("*")
                .eq("experiment_id", experiment_id)
                .gte("date", start_date)
                .order("date")
                .limit(10000)
            )

            # Aggregate by date
            daily_data = {}
            for result in results_data.data or []:
                date_str = result.get("date", "")
                if not date_str:
                    continue
                if date_str not in daily_data:
                    daily_data[date_str] = {vk: {"exposures": 0, "conversions": 0} for vk in variant_keys}

                variant_key = result.get("variant_key")
                if variant_key in daily_data[date_str]:
                    daily_data[date_str][variant_key]["exposures"] += result.get("exposures", 0)
                    daily_data[date_str][variant_key]["conversions"] += result.get("conversions", 0)

            # Format output
            trend_list = []
            for date_str in sorted(daily_data.keys()):
                day_entry = {"date": date_str}
                for variant_key in variant_keys:
                    vdata = daily_data[date_str].get(variant_key, {"exposures": 0, "conversions": 0})
                    day_entry[f"{variant_key}_exposures"] = vdata["exposures"]
                    day_entry[f"{variant_key}_conversions"] = vdata["conversions"]
                    rate = (vdata["conversions"] / vdata["exposures"] * 100) if vdata["exposures"] > 0 else 0
                    day_entry[f"{variant_key}_rate"] = round(rate, 2)
                trend_list.append(day_entry)

            return {
                "experiment_key": experiment_key,
                "variants": variant_keys,
                "days": days,
                "trend": trend_list
            }

        except Exception as e:
            logger.error(f"[ExperimentService] Failed to get daily trend for {experiment_key}: {e}")
            return None

    async def get_hourly_trend(self, experiment_key: str, hours: int = 24) -> Optional[Dict]:
        """
        Get hourly trend data for an experiment.

        Args:
            experiment_key: Experiment key
            hours: Number of hours to fetch (default 24)

        Returns:
            Trend data dict or None if experiment not found
        """
        from datetime import datetime, timedelta, timezone
        import json

        try:
            # Get experiment
            exp_result = await self._repo._execute_query(
                lambda: self._repo.client.table("experiments").select("id, variants")
                .eq("experiment_key", experiment_key)
            )

            if not exp_result or not exp_result.data:
                return None

            experiment = exp_result.data[0]
            experiment_id = experiment.get("id")
            variants = experiment.get("variants", [])

            # Parse variants
            if isinstance(variants, str):
                variants = json.loads(variants)

            variant_keys = [v.get("key") for v in variants]

            # Calculate start time
            now = datetime.now(timezone.utc)
            start_time = now - timedelta(hours=hours)
            start_date = start_time.strftime("%Y-%m-%d")

            # Query results with limit
            results_data = await self._repo._execute_query(
                lambda: self._repo.client.table("experiment_results").select("*")
                .eq("experiment_id", experiment_id)
                .gte("date", start_date)
                .order("date").order("hour")
                .limit(10000)
            )

            # Filter and format by hour
            trend_list = []
            for result in results_data.data or []:
                date_str = result.get("date", "")
                hour = result.get("hour", 0)
                variant_key = result.get("variant_key")
                time_str = f"{date_str}T{hour:02d}:00:00"

                # Parse datetime and check if within range
                try:
                    result_datetime = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    if result_datetime.tzinfo is None:
                        result_datetime = result_datetime.replace(tzinfo=timezone.utc)

                    if result_datetime < start_time:
                        continue
                except Exception:
                    continue

                # Find or create entry
                existing = next((t for t in trend_list if t.get("time") == time_str), None)
                if not existing:
                    existing = {"time": time_str}
                    for vk in variant_keys:
                        existing[f"{vk}_exposures"] = 0
                        existing[f"{vk}_conversions"] = 0
                    trend_list.append(existing)

                # Add data
                if variant_key in variant_keys:
                    existing[f"{variant_key}_exposures"] = result.get("exposures", 0)
                    existing[f"{variant_key}_conversions"] = result.get("conversions", 0)

            # Sort by time
            trend_list.sort(key=lambda x: x.get("time", ""))

            return {
                "experiment_key": experiment_key,
                "variants": variant_keys,
                "hours": hours,
                "trend": trend_list
            }

        except Exception as e:
            logger.error(f"[ExperimentService] Failed to get hourly trend for {experiment_key}: {e}")
            return None
