import { Router } from 'express';
import exampleRoutes from './example';

const router = Router();

// Add all your routes here; for example:
router.use('/example', exampleRoutes);

// You can add more routes here
// router.use('/another', anotherRoutes);

export default router;